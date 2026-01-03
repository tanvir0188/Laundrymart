import json
from uuid import uuid4

import requests
import stripe
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from laundrymart.permissions import IsCustomer
from laundrymart.settings import STRIPE_WEBHOOK_SECRET
from payment.models import Order
from payment.serializers import ConfirmOrderSerializer
from payment.utils import create_stripe_customer
from uber.utils import create_and_save_delivery, save_delivery_quote


# Create your views here.
def stripe_success(request):
  return render(request, "payments/stripe_success.html")

def stripe_cancel(request):
  return render(request, "payments/stripe_cancel.html")

class ConfirmOrderAPIView(APIView):
  permission_classes = [IsCustomer]
  @extend_schema(
    request=ConfirmOrderSerializer
  )
  def post(self, request):
    serializer = ConfirmOrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    service_type = data["service_type"]

    # Ensure Stripe customer exists (create if needed)
    stripe_customer_result = create_stripe_customer(request.user)
    if not stripe_customer_result:
      return Response({"error": "Failed to initialize payment customer"}, status=500)

    stripe_customer_id = stripe_customer_result['customer_id']

    # Check if user already has saved cards
    try:
      payment_methods = stripe.PaymentMethod.list(
        customer=stripe_customer_id,
        type="card",
      )
      has_saved_cards = len(payment_methods.data) > 0
    except Exception as e:
      return Response({"error": f"Failed to check saved cards: {str(e)}"}, status=500)

    if has_saved_cards:
      # User has saved cards → provide list and a SetupIntent client_secret for in-app card addition (optional)
      cards = []
      for pm in payment_methods.data:
        cards.append({
          'id': pm.id,
          'brand': pm.card.brand.capitalize(),
          'last4': pm.card.last4,
          'exp_month': pm.card.exp_month,
          'exp_year': pm.card.exp_year,
        })

      # Create a reusable SetupIntent for potential new card addition without redirecting to hosted page
      try:
        setup_intent = stripe.SetupIntent.create(
          customer=stripe_customer_id,
          payment_method_types=["card"],
          usage="off_session",  # since we will charge later
        )
      except Exception as e:
        return Response({"error": f"Failed to create SetupIntent: {str(e)}"}, status=500)

      return Response({
        "requires_card_save": False,
        "has_saved_cards": True,
        "cards": cards,
        "setup_intent_client_secret": setup_intent.client_secret,  # frontend can use this to add new card if user wants
        "message": "You have saved cards. Proceed to payment confirmation with selected card."
      }, status=status.HTTP_200_OK)

    else:
      # No saved cards → redirect to Stripe Checkout (setup mode) to save the first card
      protocol = "https" if request.is_secure() else "http"

      success_url = (
        f"{protocol}://{request.get_host()}"
        f"{reverse('stripe_success')}?session_id={{CHECKOUT_SESSION_ID}}"
      )

      cancel_url = (
        f"{protocol}://{request.get_host()}"
        f"{reverse('stripe_cancel')}"
      )

      try:
        session = stripe.checkout.Session.create(
          mode="setup",
          customer=stripe_customer_id,
          payment_method_types=["card"],
          success_url=success_url,
          cancel_url=cancel_url,
          metadata={
            "user_id": str(request.user.id),
            "service_type": service_type,
            "quote_id": data["quote_id"],
            "return_quote_id": data.get("return_quote_id", ""),
            "order_payload": json.dumps({
              "pickup_address": data["pickup_address"],
              "dropoff_address": data["dropoff_address"],
              "pickup_latitude": data["pickup_latitude"],
              "pickup_longitude": data["pickup_longitude"],
              "dropoff_latitude": data["dropoff_latitude"],
              "dropoff_longitude": data["dropoff_longitude"],
              "pickup_phone_number": data["pickup_phone_number"],
              "dropoff_phone_number": data["dropoff_phone_number"],
              "pickup_name": data.get("pickup_name"),
              "dropoff_name": data.get("dropoff_name"),
              "manifest_items": data.get("manifest_items", []),
              "manifest_total_value": data.get("manifest_total_value"),
              "external_store_id": data.get("external_store_id"),
              "external_id": data.get("external_id"),
              "deliverable_action": data.get("deliverable_action"),
            })
          },
        )
      except Exception as e:
        return Response({"error": f"Stripe setup failed: {str(e)}"}, status=500)

      return Response({
        "requires_card_save": True,
        "message": "Redirect to Stripe to save your card.",
        "checkout_url": session.url,
        "checkout_session_id": session.id,
      }, status=status.HTTP_200_OK)


@csrf_exempt
@transaction.atomic
def stripe_webhook_confirm_order(request):
  payload = request.body
  sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

  try:
    event = stripe.Webhook.construct_event(
      payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
  except ValueError:
    return HttpResponse(status=400)
  except stripe.error.SignatureVerificationError:
    return HttpResponse(status=400)

  # Only handle setup sessions (first-time card save via Checkout)
  if event["type"] == "checkout.session.completed":
    session = event["data"]["object"]

    # Ensure this is a setup session with no payment required
    if session.mode != "setup" or session.payment_status != "no_payment_required":
      return HttpResponse(status=200)

    # Extract metadata
    user_id = session.metadata.get("user_id")
    service_type = session.metadata.get("service_type")
    quote_id = session.metadata.get("quote_id")
    return_quote_id = session.metadata.get("return_quote_id", "")

    try:
      order_payload = json.loads(session.metadata["order_payload"])
    except (KeyError, json.JSONDecodeError):
      return HttpResponse(status=400)  # Malformed metadata

    try:
      user = User.objects.get(id=user_id)
    except User.DoesNotExist:
      return HttpResponse(status=404)

    # Retrieve the saved PaymentMethod from the SetupIntent linked to this session
    # Stripe automatically attaches it to the customer on successful setup
    try:
      setup_intent = stripe.SetupIntent.retrieve(session.setup_intent)
      payment_method_id = setup_intent.payment_method
    except Exception as e:
      # Log this — critical error
      print(f"Failed to retrieve SetupIntent or PaymentMethod: {e}")
      return HttpResponse(status=500)

    # Create the Order
    order = Order.objects.create(
      uuid=uuid4(),
      user=user,
      pickup_address=order_payload["pickup_address"],
      dropoff_address=order_payload["dropoff_address"],
      stripe_customer_id=session.customer,
      stripe_payment_method_id=payment_method_id,  # Optional: save the PM used/added
      status="card_saved",
    )

    # Proceed to create Uber delivery if service requires it
    if service_type in ["pickup", "full_service"]:
      base_payload = {
        "quote_id": quote_id,
        "pickup_address": order_payload["pickup_address"],
        "dropoff_address": order_payload["dropoff_address"],
        "pickup_phone_number": order_payload["pickup_phone_number"],
        "dropoff_phone_number": order_payload["dropoff_phone_number"],
        "external_store_id": order_payload.get("external_store_id"),
        "manifest_total_value": order_payload.get("manifest_total_value"),
        "manifest_items": order_payload.get("manifest_items", []),
        "pickup_latitude": order_payload["pickup_latitude"],
        "pickup_longitude": order_payload["pickup_longitude"],
        "dropoff_latitude": order_payload["dropoff_latitude"],
        "dropoff_longitude": order_payload["dropoff_longitude"],
        "idempotency_key": str(order.uuid),  # Recommended by Uber
      }

      try:
        if service_type == "pickup":
          base_payload.update({
            "pickup_name": order_payload.get("pickup_name", "LaundryMart"),
            "dropoff_name": user.full_name or "Customer",
            "deliverable_action": order_payload.get("deliverable_action"),
          })
          delivery = create_and_save_delivery(
            user=user,
            validated_data=order_payload,
            payload=base_payload,
            is_return_leg=False,
          )

          # Save updated quote info from actual delivery response
          save_delivery_quote(
            user=user,
            service_type=service_type,
            serializer_data=order_payload,
            uber_data={
              "id": quote_id,
              "fee": delivery.fee,
              "currency": delivery.currency or "USD",
              "currency_type": delivery.currency_type or "USD",
              "dropoff_eta": delivery.dropoff_eta,
              "dropoff_deadline": delivery.dropoff_deadline,
            },
          )

        elif service_type == "full_service":
          base_payload.update({
            "pickup_name": user.full_name or "Customer",
            "dropoff_name": order_payload.get("dropoff_name", "LaundryMart"),
            "deliverable_action": order_payload.get("deliverable_action"),
          })
          delivery = create_and_save_delivery(
            user=user,
            validated_data=order_payload,
            payload=base_payload,
            is_return_leg=False,
          )

          save_delivery_quote(
            user=user,
            service_type="full_service",
            serializer_data=order_payload,
            uber_data={
              "id": quote_id,
              "fee": delivery.fee,
              "currency": delivery.currency or "USD",
              "currency_type": delivery.currency_type or "USD",
              "dropoff_eta": delivery.dropoff_eta,
              "dropoff_deadline": delivery.dropoff_deadline,
            },
          )

        order.status = "delivery_scheduled"
        order.uber_parent_delivery_id = delivery.id  # assuming your Order model has this field
        order.save()

      except Exception as e:
        print(f"Uber delivery creation failed after card save: {e}")
        order.status = "delivery_failed"
        order.save()
        # Optional: notify admin, allow retry from frontend

    # Optional: send confirmation to user (email/push)

  return HttpResponse(status=200)

@api_view(['POST'])
@permission_classes([IsCustomer])
def charge_with_saved_method(request):
  """Process payment using saved payment method"""
  try:
    data = request.data
    amount = int(float(data.get('amount', 0)) * 100)  # Convert to cents
    service_type = data.get('service_type')
    payment_method_id = data.get('payment_method_id')

    if amount <= 0 or not service_type:
      return Response({
        'success': False,
        'error': 'Invalid amount or service type'
      }, status=400)

    # Get the customer ID
    if not request.user.stripe_customer_id:
      return Response({
        'success': False,
        'error': 'No customer profile found'
      }, status=400)

    customer_id = request.user.stripe_customer_id

    # If no payment method specified, use default
    if not payment_method_id:
      if not payment_method_id:
        return Response({
          'success': False,
          'error': 'No payment method specified'
        }, status=400)

    # Verify the payment method belongs to the customer
    try:
      pm = stripe.PaymentMethod.retrieve(payment_method_id)
      if pm.customer != customer_id:
        return Response({
          'success': False,
          'error': 'Payment method does not belong to this customer'
        }, status=403)
    except Exception:
      return Response({
        'success': False,
        'error': 'Invalid payment method'
      }, status=400)

    # Create an order
    order = Order.objects.create(
      customer=request.user,
      service_type=service_type,
      total=amount / 100,  # Convert back to dollars for storage
      payment_status='pending'
    )

    # Create and confirm payment intent
    try:
      payment_intent = stripe.PaymentIntent.create(
        amount=amount,
        currency='usd',
        customer=customer_id,
        payment_method=payment_method_id,
        off_session=True,
        confirm=True,
        metadata={
          'order_id': order.id,
          'service_type': service_type
        }
      )

      # Handle different payment states
      if payment_intent.status == 'succeeded':
        order.payment_status = 'paid'
        order.payment_id = payment_intent.id
        order.save()

        return Response({
          'success': True,
          'requires_action': False,
          'status': 'succeeded',
          'order_id': order.id
        })

      elif payment_intent.status == 'requires_action':
        order.payment_id = payment_intent.id
        order.save()

        return Response({
          'success': True,
          'requires_action': True,
          'payment_intent_client_secret': payment_intent.client_secret,
          'order_id': order.id
        })

      else:
        order.payment_status = payment_intent.status
        order.payment_id = payment_intent.id
        order.save()

        return Response({
          'success': True,
          'requires_action': False,
          'status': payment_intent.status,
          'order_id': order.id
        })

    except stripe.error.CardError as e:
      # Card declined
      order.payment_status = 'failed'
      order.save()

      return Response({
        'success': False,
        'error': e.error.message,
        'order_id': order.id
      }, status=400)

  except Exception as e:
    return Response({
      'success': False,
      'error': str(e)
    }, status=400)


@api_view(['GET'])
@permission_classes([IsCustomer])
def list_cards_from_stripe(request):
  """Fetch saved payment methods directly from Stripe"""
  try:
    # Get or create Stripe customer ID
    if not request.user.stripe_customer_id:
      customer_id = create_stripe_customer(request.user)
      if not customer_id:
        return Response({
          'success': False,
          'error': 'Failed to create customer'
        }, status=400)
    else:
      customer_id = request.user.stripe_customer_id

    # Fetch payment methods directly from Stripe
    payment_methods = stripe.PaymentMethod.list(
      customer=customer_id,
      type="card"
    )

    # Format card data for the frontend
    cards = []
    for pm in payment_methods.data:
      cards.append({
        'id': pm.id,
        'brand': pm.card.brand,
        'last4': pm.card.last4,
        'exp_month': pm.card.exp_month,
        'exp_year': pm.card.exp_year,
        # Stripe doesn't track which card is default in their API
        # You would need to store this separately if needed
      })

    return Response({
      'success': True,
      'has_cards': len(cards) > 0,
      'cards': cards
    })

  except Exception as e:
    return Response({
      'success': False,
      'error': str(e)
    }, status=400)