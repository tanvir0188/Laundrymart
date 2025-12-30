from rest_framework import serializers

from uber.models import SERVICE_TYPE_CHOICE
from uber.serializers import ManifestItemSerializer


class ConfirmOrderSerializer(serializers.Serializer):
  service_type = serializers.ChoiceField(choices=SERVICE_TYPE_CHOICE,required=True)
  quote_id = serializers.CharField(max_length=100, required=True)
  return_quote_id = serializers.CharField(max_length=100, required=False, allow_blank=True)

  pickup_address = serializers.CharField(required=True)
  dropoff_address = serializers.CharField(required=True)

  pickup_latitude = serializers.FloatField(required=True)
  pickup_longitude = serializers.FloatField(required=True)
  dropoff_latitude = serializers.FloatField(required=True)
  dropoff_longitude = serializers.FloatField(required=True)

  pickup_phone_number = serializers.CharField(max_length=30, required=True)
  dropoff_phone_number = serializers.CharField(max_length=30, required=True)

  pickup_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
  dropoff_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

  manifest_items = ManifestItemSerializer(many=True, required=False)

  manifest_total_value = serializers.IntegerField(required=False)
  external_store_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
  deliverable_action = serializers.CharField(max_length=100, required=False, allow_blank=True)

  def to_uber_delivery_payload(self):
    """Build payload for Uber Direct /deliveries endpoint"""
    data = self.validated_data
    payload = {
      "quote_id": data["quote_id"],
      "pickup_address": data["pickup_address"],
      "dropoff_address": data["dropoff_address"],
      "pickup_phone_number": data["pickup_phone_number"],
      "dropoff_phone_number": data["dropoff_phone_number"],
      "manifest_total_value": data.get("manifest_total_value"),
      "external_store_id": data.get("external_store_id"),
    }

    # Add optional fields if present
    optional = [
      "pickup_name", "dropoff_name", "external_id",
      "deliverable_action", "manifest_items",
      "pickup_latitude", "pickup_longitude",
      "dropoff_latitude", "dropoff_longitude",
    ]
    for field in optional:
      if data.get(field) is not None:
        payload[field] = data[field]

    return payload