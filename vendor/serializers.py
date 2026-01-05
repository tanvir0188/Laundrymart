from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from payment.models import Order
from uber.models import DeliveryQuote


class DashboardSerializer(serializers.Serializer):
  pending_orders = serializers.SerializerMethodField()
  this_month_completed_orders = serializers.SerializerMethodField()
  this_month_accepted_orders= serializers.SerializerMethodField()
  this_month_cancelled_orders= serializers.SerializerMethodField()
  revenue_last_seven_days = serializers.SerializerMethodField()
  recent_orders = serializers.SerializerMethodField()

  def get_pending_orders(self, obj):
    store_uuid = self.context.get('store_uuid')
    pending_orders=DeliveryQuote.objects.filter(external_store_id=store_uuid, status='pending').count()
    return pending_orders

  def get_this_month_completed_orders(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    this_month_completed_orders = Order.objects.filter(
      service_provider=associated_laundrymart,
      status='completed',
      created_at__month=obj.now.month,
      created_at__year=obj.now.year
    ).count()
    return this_month_completed_orders

  def get_this_month_accepted_orders(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    this_month_accepted_orders = Order.objects.filter(
      service_provider=associated_laundrymart,
      status='picked_up',
      created_at__month=obj.now.month,
      created_at__year=obj.now.year
    ).count()
    return this_month_accepted_orders

  def get_this_month_cancelled_orders(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    this_month_cancelled_orders = Order.objects.filter(
      service_provider=associated_laundrymart,
      status='canceled',
      created_at__month=obj.now.month,
      created_at__year=obj.now.year
    ).count()
    return this_month_cancelled_orders

  def get_revenue_last_seven_days(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    revenue = Order.objects.filter(
      service_provider=associated_laundrymart,
      status='completed',
      created_at__gte=obj.now - timedelta(days=7)
    ).aggregate(Sum('final_total_cents'))['final_total_cents__sum'] or 0
    return revenue / 100  # Convert cents to dollars

  def get_recent_orders(self, obj):
    associated_laundrymart = self.context.get('associated_laundrymart')
    recent_orders = Order.objects.filter(
      service_provider=associated_laundrymart
    ).order_by('-created_at')[:5]  # Get the 5 most recent orders
    return OrderSerializer(recent_orders, many=True).data

class OrderSerializer(serializers.ModelSerializer):
  class Meta:
    model = Order
    fields = ['uuid', 'user', 'status', 'final_total_cents', 'created_at']


