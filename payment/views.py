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
def stripe_webhook(request):
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