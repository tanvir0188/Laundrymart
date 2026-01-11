import json
import os

import requests
import stripe
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from laundrymart import settings
from laundrymart.permissions import IsCustomer, IsStaff
from payment.models import Order
from uber.cache_access_token import UBER_BASE_URL, uber_headers
from uber.models import Delivery, DeliveryQuote, ManifestItem
from uber.serializers import CreateDeliverySerializer, UberCreateQuoteSerializer
from uber.utils import create_dropoff_quote, create_full_service_quotes, create_pickup_quote, \
  save_delivery_quote


# Create your views here.
class UberCreateQuoteAPIView(APIView):
  permission_classes = [IsCustomer]

  @extend_schema(
    request=UberCreateQuoteSerializer,
    responses={
      200: OpenApiResponse(
        description="Uber delivery quote created",
        response={
          "type": "object",
          "properties": {

          }
        }
      )
    }
  )
  def post(self, request):
    serializer = UberCreateQuoteSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    customer_id = settings.UBER_CUSTOMER_ID
    service_type = serializer.validated_data.get("service_type")

    payload = serializer.to_uber_payload()
    result = {}

    if service_type == "drop_off":
      uber_data = create_dropoff_quote(customer_id, payload)
      result = {
        "service_type":service_type,
        "pickup_address":serializer.validated_data["pickup_address"],
        "dropoff_address":serializer.validated_data["dropoff_address"],
        "pickup_latitude":serializer.validated_data["pickup_latitude"],
        "pickup_longitude":serializer.validated_data["pickup_longitude"],
        "dropoff_latitude":serializer.validated_data["dropoff_latitude"],
        "dropoff_longitude":serializer.validated_data["dropoff_longitude"],
        "pickup_phone_number":serializer.validated_data["pickup_phone_number"],
        "dropoff_phone_number":serializer.validated_data["dropoff_phone_number"],
        "pickup_ready_dt": serializer.validated_data.get("pickup_ready_dt"),


        "quote_id": uber_data["id"],
        "fee": uber_data["fee"],
        "currency": uber_data["currency"],
        "currency_type": uber_data.get("currency_type"),
        "expires": uber_data["expires"],
        "dropoff_eta": uber_data.get("dropoff_eta"),
        "duration": uber_data.get("duration"),
        "pickup_duration": uber_data.get("pickup_duration"),
        "dropoff_deadline": uber_data.get("dropoff_deadline"),
      }

    elif service_type == "pickup":
      uber_data = create_pickup_quote(customer_id, payload)
      result = {
        "service_type": service_type,
        "pickup_address": serializer.validated_data["pickup_address"],
        "dropoff_address": serializer.validated_data["dropoff_address"],
        "pickup_latitude": serializer.validated_data["pickup_latitude"],
        "pickup_longitude": serializer.validated_data["pickup_longitude"],
        "dropoff_latitude": serializer.validated_data["dropoff_latitude"],
        "dropoff_longitude": serializer.validated_data["dropoff_longitude"],
        "pickup_phone_number": serializer.validated_data["pickup_phone_number"],
        "dropoff_phone_number": serializer.validated_data["dropoff_phone_number"],
        "pickup_ready_dt": serializer.validated_data.get("pickup_ready_dt"),

        "quote_id": uber_data["id"],
        "fee": uber_data["fee"],
        "currency": uber_data["currency"],
        "currency_type": uber_data.get("currency_type"),
        "expires": uber_data["expires"],
        "dropoff_eta": uber_data.get("dropoff_eta"),
        "duration": uber_data.get("duration"),
        "pickup_duration": uber_data.get("pickup_duration"),
        "dropoff_deadline": uber_data.get("dropoff_deadline"),
      }

    elif service_type == "full_service":
      # Generate payloads for each leg
      payload_to_vendor = serializer.to_uber_payload(destination="vendor")
      payload_to_customer = serializer.to_uber_payload(destination="customer")

      full_service_result = create_full_service_quotes(customer_id, payload_to_vendor, payload_to_customer)

      result = {
        "service_type": service_type,
        "pickup_address": serializer.validated_data["pickup_address"],
        "dropoff_address": serializer.validated_data["dropoff_address"],
        "pickup_latitude": serializer.validated_data["pickup_latitude"],
        "pickup_longitude": serializer.validated_data["pickup_longitude"],
        "dropoff_latitude": serializer.validated_data["dropoff_latitude"],
        "dropoff_longitude": serializer.validated_data["dropoff_longitude"],
        "pickup_phone_number": serializer.validated_data["pickup_phone_number"],
        "dropoff_phone_number": serializer.validated_data["dropoff_phone_number"],
        "pickup_ready_dt": serializer.validated_data.get("pickup_ready_dt"),

        "first_quote": full_service_result["first_quote"],
        "second_quote": full_service_result["second_quote"],
        "combined_fee": full_service_result["combined_fee"]
      }

    return Response(result)

class RequestDeliveryAPIView(APIView):
  permission_classes = [IsCustomer]
  @extend_schema(
    request=CreateDeliverySerializer,
    responses={
      200: OpenApiResponse(
        description="Uber delivery quote created",
        response={
          "type": "object",
          "properties": {

          }
        }
      )
    }
  )
  def post(self, request):
    serializer = CreateDeliverySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
      # Save DeliveryQuote
      delivery_quote = save_delivery_quote(
        user=request.user,
        service_type='drop_off',
        serializer_data=data,
        uber_data={
          "id": data["quote_id"],
          "fee": data.get("fee", 0),
          "currency": "USD"
        }
      )
    except Exception as e:
      return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      "quote_id": delivery_quote.quote_id,
      "status": "quote_saved"
    }, status=status.HTTP_201_CREATED)


class ConfirmUberDeliveryAPIView(APIView):
  @extend_schema(
    request=CreateDeliverySerializer,
    responses={
      200: OpenApiResponse(
        description="Uber delivery quote created",
        response={
          "type": "object",
          "properties": {

          }
        }
      )
    }
  )
  def post(self, request):
    serializer = CreateDeliverySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    customer_id = settings.UBER_CUSTOMER_ID

    try:
      with transaction.atomic():
        # Save DeliveryQuote
        delivery_quote = save_delivery_quote(
          user=request.user,
          service_type='drop_off',
          serializer_data=data,
          uber_data={
            "id": data["quote_id"],
            "fee": data.get("fee", 0),
            "currency": "USD"
          }
        )

        # Prepare payload
        payload = data.copy()
        payload["quote_id"] = delivery_quote.quote_id

        # Uber API call - raise exception on failure
        resp = requests.post(
          f"{UBER_BASE_URL}/customers/{customer_id}/deliveries",
          headers=uber_headers(),
          json=payload,
          timeout=10
        )
        try:
          uber_delivery_data = resp.json()
        except Exception:
          uber_delivery_data = {"error": resp.text}

        if resp.status_code >= 400:
          # Explicitly rollback and raise
          raise ValidationError({
            "error": "Uber API error",
            "details": uber_delivery_data
          })

        # Save Delivery
        delivery = Delivery.objects.create(
          quote=delivery_quote,
          customer=request.user,
          delivery_uid=uber_delivery_data.get("id"),
          pickup_name=data["pickup_name"],
          pickup_address=data["pickup_address"],
          pickup_phone_number=data["pickup_phone_number"],
          dropoff_name=data["dropoff_name"],
          dropoff_address=data["dropoff_address"],
          dropoff_phone_number=data["dropoff_phone_number"],
          external_id=data.get("external_id"),
          external_store_id=data.get("external_store_id"),
          fee=uber_delivery_data.get("fee"),
          currency=uber_delivery_data.get("currency", "USD"),
          dropoff_eta=uber_delivery_data.get("dropoff_eta"),
          dropoff_deadline=uber_delivery_data.get("dropoff_deadline"),
          deliverable_action=data.get("deliverable_action"),
          tracking_url=uber_delivery_data.get("tracking_url"),
          dropoff_latitude=data.get("dropoff_latitude"),
          dropoff_longitude=data.get("dropoff_longitude"),
          uber_raw_response=uber_delivery_data
        )

        # Save manifest items
        for item in data.get("manifest_items", []):
          ManifestItem.objects.create(
            delivery=delivery,
            name=item["name"],
            quantity=item["quantity"],
            size=item.get("size"),
            dimensions=item.get("dimensions"),
            weight=item.get("weight"),
            price=item.get("price"),
            vat_percentage=item.get("vat_percentage"),
          )

    except ValidationError as e:
      # This will contain Uber API error
      return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
      # Any other internal errors
      return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
      "delivery_id": delivery.delivery_uid,
      "quote_id": delivery_quote.quote_id,
      "status": "created",
      "uber_delivery_data": uber_delivery_data

    }, status=status.HTTP_201_CREATED)


@require_POST
@csrf_exempt
def uber_delivery_status_webhook(request):
  """
  Uber Direct delivery_status webhook - updates Delivery + Order + Stripe PaymentIntent
  """
  try:
    payload = json.loads(request.body)
    event_type = payload.get('event_type')

    if event_type != 'event.delivery_status':
      print(f"Ignoring non-status event: {event_type}")
      return HttpResponse(status=200)

    delivery_id = payload.get('delivery_id')
    if not delivery_id:
      print("Missing delivery_id")
      return HttpResponse(status=200)

    new_status = payload.get('status')
    courier_imminent = payload.get('courier_imminent', False)
    updated_at = payload.get('updated_at')

    print(f"Uber webhook | {delivery_id} → {new_status} | imminent={courier_imminent}")

    with transaction.atomic():
      delivery = Delivery.objects.select_for_update().get(delivery_uid=delivery_id)

      # Update delivery fields
      delivery.status = new_status
      delivery.courier_imminent = courier_imminent
      data = payload.get('data', {})

      if 'dropoff_eta' in data:
        delivery.dropoff_eta = data['dropoff_eta']
      if data.get('courier'):
        delivery.courier_name = data['courier'].get('name')
        delivery.courier_phone = data['courier'].get('phone_number')

      delivery.updated_at_uber = updated_at
      delivery.uber_raw_response = payload
      delivery.save(update_fields=[
        'status', 'courier_imminent', 'dropoff_eta', 'courier_name',
        'courier_phone', 'updated_at_uber', 'uber_raw_response'
      ])

      # Sync Order status
      order = _get_related_order(delivery)
      if order:
        _sync_order_status(order, new_status, courier_imminent)
        order.save(update_fields=['status'])

        # === SYNC STRIPE PAYMENTINTENT ===
        _sync_stripe_payment(order)

    return HttpResponse(status=200)

  except ObjectDoesNotExist:
    print(f"Delivery not found: {delivery_id}")
    return HttpResponse(status=200)
  except json.JSONDecodeError:
    print("Invalid JSON payload")
    return HttpResponse(status=200)
  except Exception as e:
    print("Uber webhook error")
    return HttpResponse(status=200)  # Always 200 for Uber


def _get_related_order(delivery):
  """Find related Order via your OneToOneField relations (optimized single query)"""
  # Pickup delivery case
  try:
    if hasattr(delivery, 'uber_pickup_deivery'):
      return delivery.uber_pickup_deivery
  except Order.DoesNotExist:
    pass

  # Return delivery case
  try:
    if hasattr(delivery, 'uber_return_delivery'):
      return delivery.uber_return_delivery
  except Order.DoesNotExist:
    pass

  return None


def _sync_order_status(order, delivery_status, courier_imminent):
  """Map Uber status → Order status (your existing logic)"""
  status_map = {
    'pending': 'processing',
    'pickup': 'picked_up' if not courier_imminent else 'pickup_en_route',
    'pickup_complete': 'picked_up',
    'dropoff': 'delivery_en_route' if not courier_imminent else 'courier_near_dropoff',
    'delivered': 'completed',
    'canceled': 'canceled',
    'returned': 'return_scheduled',
  }

  new_status = status_map.get(delivery_status)
  if new_status and order.status != new_status:
    order.status = new_status
    print(f"Order {order.uuid} → {new_status} (delivery: {delivery_status})")


def _sync_stripe_payment(order):
  """
  Sync Stripe PaymentIntent status with delivery progress
  Only if PaymentIntent exists (post-paid flow)
  """
  # Check if we have a Stripe PaymentIntent (created after weighing)
  if not hasattr(order, 'payment') or not order.payment:
    return  # No payment yet - normal for early delivery stages

  payment_intent_id = order.payment.stripe_payment_intent_id
  if not payment_intent_id:
    return

  try:
    # Fetch current PaymentIntent status from Stripe (optimized: single API call)
    pi = stripe.PaymentIntent.retrieve(
      payment_intent_id,
      expand=['payment_method']
    )

    current_pi_status = pi.status
    our_payment_status = order.payment.status

    # Update our Payment model if Stripe status changed
    if current_pi_status != our_payment_status:
      order.payment.status = current_pi_status
      order.payment.save(update_fields=['status'])

      print(
        f"Order {order.uuid} Stripe sync | PI {payment_intent_id} → {current_pi_status}"
      )

      # Optional: Trigger business actions based on payment status + delivery status
      _handle_payment_delivery_sync(order, current_pi_status)

  except stripe.error.StripeError as e:
    print(f"Stripe sync failed for PI {payment_intent_id}: {str(e)}")
  except Exception as e:
    print(f"Payment sync error for order {order.uuid}: {str(e)}")


def _handle_payment_delivery_sync(order, pi_status):
  """
  Business logic when payment + delivery status align
  Examples for your post-paid laundry flow:
  """
  # Example 1: Delivery completed + payment succeeded → mark order fully complete
  if (order.status == 'completed' and pi_status in ['succeeded', 'requires_capture']):
    if order.status != 'completed':  # idempotent
      order.status = 'completed'
      print(f"Order {order.uuid} fully completed (payment+delivery)")

  # Example 2: Delivery canceled + payment pending → cancel/refund payment
  elif (order.status == 'canceled' and pi_status == 'requires_capture'):
    try:
      stripe.PaymentIntent.cancel(
        order.payment.stripe_payment_intent_id,
        cancellation_reason='requested_by_customer|abandoned'
      )
      print(f"Auto-canceled PI for canceled order {order.uuid}")
    except stripe.error.StripeError:
      pass  # let manual refund handle it

  # Example 3: Payment failed + delivery in progress → notify store/customer
  elif (pi_status in ['requires_payment_method', 'requires_confirmation'] and
        order.status in ['picked_up', 'delivery_en_route']):
    print(f"Payment issue detected on active delivery {order.uuid}")