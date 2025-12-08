from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
# Create your models here.


class CustomUserManager(BaseUserManager):

  def _create_user(self, password, email=None, phone_number=None, full_name=None, **extra_fields):
    if not email and not phone_number:
      raise ValueError('Either email or phone number must be provided.')

    if email:
      email = self.normalize_email(email)

    user = self.model(
      email=email,
      phone_number=phone_number,
      full_name=full_name,
      **extra_fields
    )
    user.set_password(password)
    user.save(using=self._db)
    return user

  def create_user(self, password, email=None, phone_number=None, full_name=None, **extra_fields):
    extra_fields.setdefault('is_superuser', False)
    extra_fields.setdefault('is_staff', False)
    return self._create_user(password, email, phone_number, full_name, **extra_fields)

  def create_superuser(self,password, email=None, phone_number=None, full_name=None, **extra_fields):
    extra_fields.setdefault('is_superuser', True)
    extra_fields.setdefault('is_staff', True)
    extra_fields.setdefault('is_active', True)

    if extra_fields.get('is_superuser') is not True:
      raise ValueError('Superuser must have is_superuser=True.')

    return self._create_user(password, email, phone_number, full_name, **extra_fields)

class User(AbstractUser):
  username = None
  full_name = models.CharField(blank=True, max_length=255, null=True)
  email = models.EmailField(blank=True, null=True, unique=True, db_index=True)
  phone_number = models.CharField(blank=True, null=True, unique=True, max_length=30)
  location=models.TextField(blank=True, null=True)
  lat = models.CharField(max_length=100, blank=True, null=True)
  lng = models.CharField(max_length=100,blank=True, null=True)

  secondary_location=models.TextField(blank=True, null=True)
  secondary_lat = models.CharField(max_length=100, blank=True, null=True)
  secondary_lng = models.CharField(max_length=100,blank=True, null=True)

  is_active = models.BooleanField(default=False)
  otp = models.CharField(blank=True, null=True, max_length=4)
  otp_expires=models.DateTimeField(blank=True, null=True)
  is_verified = models.BooleanField(default=False)

  is_tester=models.BooleanField(default=False)

  laundrymart_name=models.CharField(max_length=255, blank=True, null=True)

  price_per_pound=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  service_fee=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  minimum_order_weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  daily_capacity_limit=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_sunday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_sunday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_monday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_monday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_tuesday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_tuesday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_wednesday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_wednesday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_thursday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_thursday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_friday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_friday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  turnaround_time_minimum_saturday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
  turnaround_time_maximum_saturday = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

  operating_hours_start_sunday = models.TimeField(blank=True, null=True)
  operating_hours_end_sunday = models.TimeField(blank=True, null=True)
  is_closed_sunday = models.BooleanField(default=False)

  operating_hours_start_monday = models.TimeField(blank=True, null=True)
  operating_hours_end_monday = models.TimeField(blank=True, null=True)
  is_closed_monday = models.BooleanField(default=False)

  operating_hours_start_tuesday = models.TimeField(blank=True, null=True)
  operating_hours_end_tuesday = models.TimeField(blank=True, null=True)
  is_closed_tuesday = models.BooleanField(default=False)

  operating_hours_start_wednesday = models.TimeField(blank=True, null=True)
  operating_hours_end_wednesday = models.TimeField(blank=True, null=True)
  is_closed_wednesday = models.BooleanField(default=False)

  operating_hours_start_thursday = models.TimeField(blank=True, null=True)
  operating_hours_end_thursday = models.TimeField(blank=True, null=True)
  is_closed_thursday = models.BooleanField(default=False)

  operating_hours_start_friday = models.TimeField(blank=True, null=True)
  operating_hours_end_friday = models.TimeField(blank=True, null=True)
  is_closed_friday = models.BooleanField(default=False)

  operating_hours_start_saturday = models.TimeField(blank=True, null=True)
  operating_hours_end_saturday = models.TimeField(blank=True, null=True)
  is_closed_saturday = models.BooleanField(default=False)

  created_at=models.DateTimeField(auto_now_add=True)
  updated_at=models.DateTimeField(auto_now=True)

  image=models.ImageField(blank=True, null=True, upload_to='images/')

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = []

  objects = CustomUserManager()

  def clean(self):
    # Ensure at least one identifier is present
    if not self.email and not self.phone_number:
      raise ValidationError('Either email or phone number must be provided.')

  def save(self, *args, **kwargs):
    self.full_clean()  # enforce `clean()` before save
    super().save(*args, **kwargs)

  def __str__(self):
    return self.full_name or self.email or self.phone_number or str(self.pk)

  class Meta:
    verbose_name = 'User'
    verbose_name_plural = 'Users'


