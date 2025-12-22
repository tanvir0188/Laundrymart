from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import User


# Create your models here.
DELIVERY_CHOICE=[

]
class DeliveryQuote(models.Model):
  delivery_style=models.CharField(max_length=50, blank=True, null=True)
  quote_id = models.CharField(blank=True, null=True,unique=True, max_length=255)
  customer=models.ForeignKey(User, on_delete=models.CASCADE, related_name='delivery_quotes')
  pickup_address=models.TextField(blank=True, null=True)
  dropoff_address=models.TextField(blank=True, null=True)
  pickup_latitude=models.FloatField(blank=True, null=True)
  pickup_longitude=models.FloatField(blank=True, null=True)
  dropoff_latitude=models.FloatField(blank=True, null=True)
  pickup_phone_number=models.CharField(blank=True, null=True, max_length=50)
  dropoff_phone_number=models.CharField(blank=True, null=True, max_length=50)
  manifest_total_value=models.DecimalField(max_digits=12, decimal_places=2,blank=True, null=True, validators=[MinValueValidator(0)])
  external_store_id=models.CharField(blank=True, null=True)

  fee=models.DecimalField(blank=True, null=True, max_digits=10, decimal_places=2)
  currency=models.CharField(max_length=20, blank=True, null=True)
  currency_type=models.CharField(max_length=20, blank=True, null=True)
  dropoff_eta=models.DateTimeField(blank=True, null=True)

  duration = models.PositiveIntegerField( blank=True, null=True, help_text="Estimated total duration in minutes")
  pickup_duration = models.PositiveIntegerField(blank=True, null=True,help_text="Estimated pickup duration in minutes")

  dropoff_deadline = models.DateTimeField(blank=True, null=True)

  created=models.DateTimeField(blank=True, null=True)
  expires=models.DateTimeField(blank=True, null=True)

  saved_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    verbose_name = "Uber Direct Delivery Quote"
    verbose_name_plural = "Uber Direct Delivery Quotes"
    ordering = ['-saved_at']


  def __str__(self):
    return f"Quote {self.quote_id} - ${self.fee if self.fee else 0} - Expires {self.expires}"

class Delivery(models.Model):
  delivery_id = models.CharField(max_length=255,unique=True,blank=True,null=True)

  quote = models.OneToOneField(DeliveryQuote,on_delete=models.CASCADE,null=True,blank=True)

  customer = models.ForeignKey(
    'User',
    on_delete=models.CASCADE,
    related_name='deliveries'
  )

  # Core request fields
  quote_id = models.CharField(max_length=255, blank=True, null=True)
  idempotency_key = models.CharField(max_length=255, blank=True, null=True, unique=True)

  pickup_name = models.CharField(max_length=255, blank=True, null=True)
  pickup_address = models.TextField(blank=True, null=True)
  pickup_phone_number = models.CharField(max_length=30, blank=True, null=True)
  pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
  pickup_longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
  pickup_notes = models.TextField(blank=True, null=True)
  pickup_business_name = models.CharField(max_length=255, blank=True, null=True)

  dropoff_name = models.CharField(max_length=255, blank=True, null=True)
  dropoff_address = models.TextField(blank=True, null=True)
  dropoff_phone_number = models.CharField(max_length=30, blank=True, null=True)
  dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
  dropoff_longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
  dropoff_notes = models.TextField(blank=True, null=True)
  dropoff_seller_notes = models.TextField(blank=True, null=True)
  dropoff_business_name = models.CharField(max_length=255, blank=True, null=True)

  manifest_reference = models.CharField(max_length=255, blank=True, null=True)
  manifest_total_value = models.DecimalField(
    max_digits=12, decimal_places=2,
    blank=True, null=True,
    validators=[MinValueValidator(0)]
  )

  external_store_id = models.CharField(max_length=100, blank=True, null=True)
  external_id = models.CharField(max_length=100, blank=True, null=True)

  deliverable_action = models.CharField(max_length=100, blank=True,
                                        null=True)  # e.g., deliverable_action_meet_at_door

  # Response fields from Uber (updated via webhook or polling)
  status = models.CharField(max_length=50, blank=True, null=True)  # e.g., pending, driver_en_route, completed
  fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # In cents
  currency = models.CharField(max_length=3, default='usd')
  tracking_url = models.URLField(blank=True, null=True)
  dropoff_eta = models.DateTimeField(blank=True, null=True)
  dropoff_deadline = models.DateTimeField(blank=True, null=True)

  courier_name = models.CharField(max_length=255, blank=True, null=True)
  courier_phone = models.CharField(max_length=30, blank=True, null=True)
  courier_vehicle_type = models.CharField(max_length=50, blank=True, null=True)

  created_at_uber = models.DateTimeField(blank=True, null=True)
  updated_at_uber = models.DateTimeField(blank=True, null=True)

  # Local timestamps
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    verbose_name = "Uber Direct Delivery"
    verbose_name_plural = "Uber Direct Deliveries"
    ordering = ['-created_at']

  def __str__(self):
    return f"Delivery {self.delivery_id or 'Pending'} - {self.external_id or self.pk}"