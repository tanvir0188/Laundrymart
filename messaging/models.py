from django.db import models

from accounts.models import User


# Create your models here.

class Notification(models.Model):
	# category = models.CharField(choices=NOTIFICATION_CATEGORY_CHOICES, default='Normal', max_length=255)
	custom_title=models.CharField(blank=True, null=True, max_length=255)
	recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
	text = models.TextField(blank=False, null=False, max_length=1000)
	target_url = models.CharField(max_length=255, null=True, blank=True)
	additional_info= models.JSONField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	is_read = models.BooleanField(default=False)
	seen = models.BooleanField(default=False)

	def __str__(self):
		return self.text
	class Meta:
		ordering = ['-created_at']
