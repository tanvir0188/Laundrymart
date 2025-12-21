from rest_framework import serializers

from accounts.models import Service, User
from common_utils.distance_utils import calculate_distance_miles, get_best_location

class ServiceSerializer(serializers.ModelSerializer):
  class Meta:
    model = Service
    fields = '__all__'

class VendorSerializer(serializers.ModelSerializer):
  distance=serializers.SerializerMethodField()
  vendor_services = ServiceSerializer(many=True, read_only=True)

  class Meta:
    model = User
    fields = ['id', 'laundrymart_name','image', 'location','lat', 'lng', 'vendor_description', 'distance','price_per_pound',

              'average_rating','get_turnaround_time','is_open_now', 'closes_at', 'vendor_services',

              'operating_hours_start_sunday', 'operating_hours_end_sunday', 'is_closed_sunday',
              'operating_hours_start_monday', 'operating_hours_end_monday', 'is_closed_monday',
              'operating_hours_start_tuesday', 'operating_hours_end_tuesday', 'is_closed_tuesday',
              'operating_hours_start_wednesday', 'operating_hours_end_wednesday', 'is_closed_wednesday',
              'operating_hours_start_thursday', 'operating_hours_end_thursday', 'is_closed_thursday',
              'operating_hours_start_friday', 'operating_hours_end_friday', 'is_closed_friday',
              'operating_hours_start_saturday', 'operating_hours_end_saturday', 'is_closed_saturday'
              ]
  def get_distance(self, obj):
    value = getattr(obj, 'distance', None)
    return round(value, 1)


  # def get_distance(self, obj):
  #   annotated_distance = getattr(obj, 'distance', None)
  #   if annotated_distance is not None:
  #     return round(annotated_distance, 1) if annotated_distance else None
  #
  #   # Fallback: Python calculation (only if serializer used outside this view)
  #   request = self.context.get('request')
  #   if not request or not request.user.is_authenticated:
  #     return None
  #
  #   user = request.user
  #   #vendor_lat, vendor_lng = get_best_location(obj)
  #
  #   return calculate_distance_miles(user.lat, user.lng, obj.lat, obj.lng)

