import json
from uuid import uuid4

import requests
import stripe
from django.db import transaction
from django.http import HttpResponse
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

    # Ensure Stripe customer exists
    stripe_customer_id = create_stripe_customer(request.user)
    if not stripe_customer_id:
      return Response({"error": "Failed to initialize payment customer"}, status=500)

    # Create Checkout Session in setup mode
    protocol = "https" if request.is_secure() else "http"
    success_url = f"{protocol}://{request.get_host()}{reverse('stripe-setup-success')}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{protocol}://{request.get_host()}{reverse('stripe-setup-cancel')}"

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
          # Store all needed data as JSON string if too large
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
      "message": "Redirect to Stripe to save your card.",
      "checkout_url": session.url,
      "checkout_session_id": session.id,
    }, status=status.HTTP_200_OK)

@csrf_exempt
@transaction.atomic
def stripe_webhook_confirm_order(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        if session.mode != "setup" or session.payment_status != "no_payment_required":
            return HttpResponse(status=200)

        user_id = session.metadata["user_id"]
        service_type = session.metadata["service_type"]
        order_payload = json.loads(session.metadata["order_payload"])

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse(status=200)

        # Create Order now that card is saved
        order = Order.objects.create(
            uuid=uuid4(),
            user=user,
            pickup_address=order_payload["pickup_address"],
            dropoff_address=order_payload["dropoff_address"],
            stripe_customer_id=session.customer,
            status="card_saved",  # or "awaiting_delivery"
        )

        # Create Uber delivery only if needed
        if service_type in ["pickup", "full_service"]:
            base_payload = {
                "quote_id": session.metadata["quote_id"],
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
            }

            try:
                if service_type == "pickup":
                    base_payload.update({
                        "pickup_name": order_payload.get("pickup_name", "LaundryMart"),
                        "dropoff_name": user.full_name or "Customer",
                    })
                    delivery = create_and_save_delivery(
                        user=user,
                        validated_data=order_payload,
                        payload=base_payload,
                        is_return_leg=False,
                    )
                    save_delivery_quote(
                        user=user,
                        service_type=service_type,
                        serializer_data=order_payload,
                        uber_data={
                          "id": session.metadata["quote_id"],
                          "fee": delivery.fee,
                          "currency": delivery.currency or "USD",
                          "currency_type": delivery.currency or "USD",
                          # Uber returns currency_type in quote, but delivery may not have it
                          "dropoff_eta": delivery.dropoff_eta,
                          "duration": None,  # not available after delivery creation
                          "pickup_duration": None,
                          "dropoff_deadline": delivery.dropoff_deadline,
                          "expires": None,  # quote already used, no longer relevant
                        },
                    )

                elif service_type == "full_service":
                    base_payload.update({
                        "pickup_name": user.full_name or "Customer",
                        "dropoff_name": order_payload.get("dropoff_name", "LaundryMart"),
                    })
                    delivery = create_and_save_delivery(
                        user=user,
                        validated_data=order_payload,
                        payload=base_payload,
                        is_return_leg=False,
                    )
                    save_delivery_quote(
                        user=user,
                        service_type="full_service_dropoff",
                        serializer_data=order_payload,
                        uber_data={
                          "id": session.metadata["quote_id"],
                          "fee": delivery.fee,
                          "currency": delivery.currency or "USD",
                          "currency_type": delivery.currency or "USD",
                          "dropoff_eta": delivery.dropoff_eta,
                          "duration": None,  # not available after delivery creation
                          "pickup_duration": None,
                          "dropoff_deadline": delivery.dropoff_deadline,
                          "expires": None,  # quote already used, no longer relevant
                        },
                    )

                order.status = "delivery_scheduled"
                order.save()

            except Exception as e:
                # Uber failed — keep order, card is still saved
                order.status = "delivery_failed"
                order.save()
                # Optional: notify admin or queue retry

        # Optional: send confirmation email/SMS

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