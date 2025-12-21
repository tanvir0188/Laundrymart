from django.db import models

from accounts.models import User


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
  vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
  rating = models.IntegerField(choices=REVIEW_CHOICES, default=1)
  created_at = models.DateTimeField(auto_now_add=True)

  class Meta:
    unique_together = ('user', 'vendor')  # Enforces one review per user per vendor
    ordering = ['-created_at']  # Newest first
    verbose_name = 'Review'
    verbose_name_plural = 'Reviews'


  def __str__(self):
    return f"{self.user.full_name or self.user.email} → {self.vendor.laundrymart_name or self.vendor.email} ({self.rating}★)"



