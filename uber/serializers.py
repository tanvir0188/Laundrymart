from rest_framework import serializers

from uber.models import DeliveryQuote


class UberCreateQuoteSerializer(serializers.Serializer):
  pickup_address = serializers.CharField()
  dropoff_address = serializers.CharField()

  pickup_latitude = serializers.FloatField(required=False)
  pickup_longitude = serializers.FloatField(required=False)
  dropoff_latitude = serializers.FloatField(required=False)
  dropoff_longitude = serializers.FloatField(required=False)

  pickup_ready_dt = serializers.DateTimeField(required=False)
  pickup_deadline_dt = serializers.DateTimeField(required=False)
  dropoff_ready_dt = serializers.DateTimeField(required=False)
  dropoff_deadline_dt = serializers.DateTimeField(required=False)

  pickup_phone_number = serializers.RegexField(r'^\+[0-9]+$')
  dropoff_phone_number = serializers.RegexField(r'^\+[0-9]+$')

  manifest_total_value = serializers.IntegerField(min_value=0)

  external_store_id = serializers.CharField(required=False, allow_blank=True)

  def to_uber_payload(self, destination=None):

    data = self.validated_data
    import json  # Can be at top, but safe here too

    # Build structured address dict from free-text string
    def build_address_struct(address_str):
      return {
        "street_address": [address_str.strip()],
        "city": "",
        "state": "",
        "zip_code": "",
        "country": "US",  # Adjust if needed
      }

    pickup_address = data["pickup_address"]
    dropoff_address = data["dropoff_address"]

    # Swap pickup/dropoff based on destination
    if destination == "vendor":
      # Leg 1: customer -> vendor
      pickup_address, dropoff_address = pickup_address, dropoff_address
    elif destination == "customer":
      # Leg 2: vendor -> customer
      pickup_address, dropoff_address = dropoff_address, pickup_address

    pickup_struct = build_address_struct(pickup_address)
    dropoff_struct = build_address_struct(dropoff_address)

    payload = {
      "pickup_address": json.dumps(pickup_struct),
      "dropoff_address": json.dumps(dropoff_struct),
      "pickup_phone_number": data["pickup_phone_number"],
      "dropoff_phone_number": data["dropoff_phone_number"],
      "manifest_total_value": data["manifest_total_value"],
    }

    # Add optional lat/long if provided
    if data.get("pickup_latitude") is not None and data.get("pickup_longitude") is not None:
      payload["pickup_latitude"] = data["pickup_latitude"]
      payload["pickup_longitude"] = data["pickup_longitude"]

    if data.get("dropoff_latitude") is not None and data.get("dropoff_longitude") is not None:
      payload["dropoff_latitude"] = data["dropoff_latitude"]
      payload["dropoff_longitude"] = data["dropoff_longitude"]

    if data.get("external_store_id"):
      payload["external_store_id"] = data["external_store_id"]

    # Optional datetime fields (Uber expects ISO 8601 strings if provided)
    # Example: if data.get("pickup_ready_dt"):
    #   payload["pickup_ready_time"] = data["pickup_ready_dt"].isoformat() + "Z"

    return payload

class DeliveryQuoteSerializer(serializers.ModelSerializer):
  class Meta:
    model=DeliveryQuote
    fields=[]
