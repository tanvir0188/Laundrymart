import os

import requests
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from laundrymart import settings
from laundrymart.permissions import IsCustomer, IsStaff
from uber.cache_access_token import UBER_BASE_URL, uber_headers
from uber.models import Delivery, DeliveryQuote, ManifestItem
from uber.serializers import CreateDeliverySerializer, UberCreateQuoteSerializer
from uber.utils import create_dropoff_quote, create_full_service_quotes, create_pickup_quote, save_delivery_quote


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