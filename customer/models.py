from django.db import models

from accounts.models import LaundrymartStore, User
from payment.models import Order
from uber.models import DeliveryQuote

# Create your models here.
REVIEW_CHOICES = [
  (1, 1),
  (2, 2),
  (3, 3),
  (4, 4),
  (5, 5),

]
class Review(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
  laundrymart = models.ForeignKey(LaundrymartStore, on_delete=models.CASCADE, related_name='received_reviews')
  comment = models.TextField(blank=True, null=True)
  rating = models.IntegerField(choices=REVIEW_CHOICES, default=1)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    ordering = ['-created_at']  # Newest first
    verbose_name = 'Review'
    verbose_name_plural = 'Reviews'


  def __str__(self):
    return f"{self.user.full_name or self.user.email} -> {self.laundrymart.laundrymart_name} ({self.rating}★)"

class OrderReport(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filed_reports')
  delivery_quote=models.OneToOneField(DeliveryQuote, on_delete=models.CASCADE, related_name='filed_report')
  order=models.OneToOneField(Order, on_delete=models.CASCADE, related_name='filed_report')
  issue_description = models.TextField()

  created_at = models.DateTimeField(auto_now_add=True)

class OrderReportImage(models.Model):
  report = models.ForeignKey(OrderReport, on_delete=models.CASCADE, related_name='images')
  image = models.ImageField(upload_to='order_customer_report_images/')
  uploaded_at = models.DateTimeField(auto_now_add=True)
  def __str__(self):
    return f"Image for Report {self.report.id} uploaded at {self.uploaded_at}"


