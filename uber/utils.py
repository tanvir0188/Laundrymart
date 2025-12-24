import requests

from uber.cache_access_token import UBER_BASE_URL, uber_headers
from uber.models import Delivery, DeliveryQuote
from uber.serializers import DeliveryQuoteCreateSerializer


def create_dropoff_quote(customer_id, payload):
  resp = requests.post(
    f"{UBER_BASE_URL}/customers/{customer_id}/delivery_quotes",
    headers=uber_headers(),
    json=payload,
    timeout=10
  )
  resp.raise_for_status()
  return resp.json()


def create_pickup_quote(customer_id, payload):
  resp = requests.post(
    f"{UBER_BASE_URL}/customers/{customer_id}/delivery_quotes",
    headers=uber_headers(),
    json=payload,
    timeout=10
  )
  resp.raise_for_status()
  return resp.json()


def create_full_service_quotes(customer_id, payload_to_vendor, payload_to_customer):
  # First quote: customer -> vendor
  quote1 = create_dropoff_quote(customer_id, payload_to_vendor)

  # Second quote: vendor -> customer
  quote2 = create_pickup_quote(customer_id, payload_to_customer)

  # Combine fees
  combined_fee = quote1["fee"] + quote2["fee"]

  return {
    "first_quote": quote1,
    "second_quote": quote2,
    "combined_fee": combined_fee
  }


def save_delivery_quote(*, user, service_type, serializer_data, uber_data):
  return DeliveryQuote.objects.create(
    service_type=service_type,
    quote_id=uber_data["id"],
    customer=user,
    pickup_address=serializer_data.get("pickup_address"),
    dropoff_address=serializer_data.get("dropoff_address"),
    pickup_latitude=serializer_data.get("pickup_latitude"),
    pickup_longitude=serializer_data.get("pickup_longitude"),
    dropoff_latitude=serializer_data.get("dropoff_latitude"),
    dropoff_longitude=serializer_data.get("dropoff_longitude"),
    pickup_phone_number=serializer_data.get("pickup_phone_number"),
    dropoff_phone_number=serializer_data.get("dropoff_phone_number"),
    manifest_total_value=serializer_data.get("manifest_total_value"),
    external_store_id=serializer_data.get("external_store_id"),
    fee=uber_data.get("fee"),
    currency=uber_data.get("currency"),
    currency_type=uber_data.get("currency_type"),
    dropoff_eta=uber_data.get("dropoff_eta"),
    duration=uber_data.get("duration"),
    pickup_duration=uber_data.get("pickup_duration"),
    dropoff_deadline=uber_data.get("dropoff_deadline"),
    expires=uber_data.get("expires"),
  )
