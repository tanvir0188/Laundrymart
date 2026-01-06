from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import serializers

from messaging.models import VendorNotification
from messaging.serializers import VendorNotificationSerializer
from payment.models import Order
from uber.models import DeliveryQuote


class DashboardSerializer(serializers.Serializer):
  order_stats=serializers.SerializerMethodField()
  # revenue_last_seven_days = serializers.SerializerMethodField()
  recent_orders = serializers.SerializerMethodField()
  alert_notifications=serializers.SerializerMethodField()

  def get_order_stats(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    store_uuid = self.context.get('store_uuid')
    print('store_uuid:', store_uuid)

    current_month = timezone.now().month
    current_year = timezone.now().year
    print('current_month:', current_month, 'current_year:', current_year)

    # Query to get the counts for all the statuses in a single query
    order_stats = DeliveryQuote.objects.filter(
      external_store_id=store_uuid,
      saved_at__month=current_month,
      saved_at__year=current_year
    ).aggregate(
      pending_orders=Count('id', filter=Q(status='pending')),
      accepted_orders=Count('id', filter=Q(status='accepted')),
      cancelled_orders=Count('id', filter=Q(status='rejected'))
    )
    print('Order Stats:', order_stats)
    completed_orders = Order.objects.filter(service_provider=associated_laundrymart, status='completed').count()

    # Returning the aggregated counts
    return {
      'pending_orders': order_stats['pending_orders'],
      'completed_orders': completed_orders,
      'accepted_orders': order_stats['accepted_orders'],
      'cancelled_orders': order_stats['cancelled_orders'],
    }

  # Convert cents to dollars
  #
  def get_alert_notifications(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    notifications = VendorNotification.objects.filter(recipient=associated_laundrymart, category='Important', is_read=False).order_by('-created_at')[:2]
    return VendorNotificationSerializer(notifications, many=True).data

  def get_recent_orders(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    recent_orders = Order.objects.filter(
      service_provider=associated_laundrymart
    ).only('id', 'uuid', 'user_id', 'status', 'weight_in_pounds', 'created_at', 'service_provider_id').order_by('-created_at')[:5]  # Get the 5 most recent orders
    return OrderSerializer(recent_orders, many=True, context={'associated_laundrymart':associated_laundrymart}).data

class OrderSerializer(serializers.ModelSerializer):
  user = serializers.StringRelatedField()
  price=serializers.SerializerMethodField()
  class Meta:
    model = Order
    fields = ['id','uuid', 'user', 'status', 'weight_in_pounds','price', 'created_at']
  def get_price(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    store_fee = associated_laundrymart.price_per_pound
    total_fee = store_fee * obj.weight_in_pounds+(associated_laundrymart.service_fee or 0)
    return round(total_fee,2)


