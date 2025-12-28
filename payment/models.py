from django.db import models

# Create your models here.
# orders/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid

from accounts.models import User


class Order(models.Model):
  """
  Main order for laundry pickup → weigh → return delivery
  """
  uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
  service_provider=models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_orders', blank=True, null=True)

  # Addresses (stored as JSON strings to match Uber format – you can change later if needed)
  pickup_address = models.JSONField(blank=True, null=True)
  dropoff_address = models.JSONField(blank=True, null=True)

  # Uber tracking
  uber_pickup_quote_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
  uber_pickup_delivery_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
  uber_return_quote_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
  uber_return_delivery_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

  # Stripe
  stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
  stripe_default_pm_id = models.CharField(max_length=100, blank=True, null=True)  # saved payment method

  # Pricing
  weight_in_pounds = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
  service_charge_cents = models.PositiveIntegerField(blank=True, null=True)  # your laundry fee
  delivery_fee_cents = models.PositiveIntegerField(blank=True, null=True)   # final Uber fee
  final_total_cents = models.PositiveIntegerField(blank=True, null=True)

  # Status flow
  STATUS_CHOICES = [
    ('pending_setup', 'Pending Card Setup'),
    ('card_saved', 'Card Saved – Awaiting Pickup'),
    ('picked_up', 'Picked Up'),
    ('weighed', 'Weighed & Priced'),
    ('charged', 'Charged'),
    ('return_scheduled', 'Return Delivery Scheduled'),
    ('completed', 'Completed'),
    ('canceled', 'Canceled'),
  ]
  status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_setup')

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    indexes = [
      models.Index(fields=['status']),
      models.Index(fields=['user']),
      models.Index(fields=['stripe_customer_id']),
    ]
    ordering = ['-created_at']

  def __str__(self):
    return f"Order {self.uuid} – {self.user} – {self.status}"


class Payment(models.Model):
  """
  Final charge record (one-to-one with Order)
  """
  order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
  stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
  amount_cents = models.PositiveIntegerField()
  status = models.CharField(max_length=20, default='pending')  # succeeded, failed, etc.
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f"Payment {self.stripe_payment_intent_id} for Order {self.order.uuid}"