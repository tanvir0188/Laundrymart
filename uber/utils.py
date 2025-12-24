import requests

from uber.cache_access_token import UBER_BASE_URL, uber_headers


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