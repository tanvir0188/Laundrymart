import requests

from laundrymart.settings import UBER_CUSTOMER_ID
from uber.cache_access_token import UBER_BASE_URL, uber_headers
from uber.models import Delivery, DeliveryQuote, ManifestItem


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
    customer_note=serializer_data.get("customer_note"),
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

def create_uber_delivery( payload, headers):
    """
    Low-level call to Uber Direct /deliveries endpoint.
    Returns the parsed JSON response.
    """
    resp = requests.post(
      f"{UBER_BASE_URL}/customers/{UBER_CUSTOMER_ID}/deliveries",
      headers=headers,
      json=payload,
      timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def create_and_save_delivery(
    *,
    user,
    validated_data,  # from ConfirmOrderSerializer.validated_data
    payload,
    is_return_leg=False,
):
  """
  Creates Uber delivery and saves it + manifest items to DB.
  Reusable for both pickup and full_service legs.
  """
  customer_id = UBER_CUSTOMER_ID
  headers = uber_headers()  # your existing function

  uber_data = create_uber_delivery(payload, headers)

  # Determine which lat/lng to use for dropoff (important for return leg)
  dropoff_lat = (
    validated_data["pickup_latitude"]
    if is_return_leg
    else validated_data["dropoff_latitude"]
  )
  dropoff_lng = (
    validated_data["pickup_longitude"]
    if is_return_leg
    else validated_data["dropoff_longitude"]
  )

  delivery = Delivery.objects.create(
    customer=user,
    delivery_uid=uber_data["id"],
    pickup_name=payload.get("pickup_name"),
    pickup_address=payload["pickup_address"],
    pickup_phone_number=payload["pickup_phone_number"],
    dropoff_name=payload.get("dropoff_name"),
    dropoff_address=payload["dropoff_address"],
    dropoff_phone_number=payload["dropoff_phone_number"],
    external_id=validated_data.get("external_id"),
    external_store_id=validated_data.get("external_store_id"),
    fee=uber_data.get("fee"),
    currency=uber_data.get("currency", "USD"),
    dropoff_eta=uber_data.get("dropoff_eta"),
    dropoff_deadline=uber_data.get("dropoff_deadline"),
    deliverable_action=validated_data.get("deliverable_action"),
    tracking_url=uber_data.get("tracking_url"),
    dropoff_latitude=dropoff_lat,
    dropoff_longitude=dropoff_lng,
    uber_raw_response=uber_data,
  )

  # Save manifest items using already-validated data
  for item in validated_data.get("manifest_items", []):
    ManifestItem.objects.create(delivery=delivery, **item)

  return delivery
