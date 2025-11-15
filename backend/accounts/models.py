from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
# Create your models here.


class CustomUserManager(BaseUserManager):

  def _create_user(self, password, email=None, phone_number=None , full_name=None, **extra_fields):
    if not email:
      raise ValueError('Users must have an email address')

    email = self.normalize_email(email)
    user = self.model(email=email,phone_number=phone_number, full_name=full_name, **extra_fields)
    user.set_password(password)
    user.save(using=self._db)
    return user

  def create_user(self, password,email=None, phone_number=None,full_name=None, **extra_fields):
    extra_fields.setdefault('is_superuser', False)
    extra_fields.setdefault('is_staff', False)
    return self._create_user(password, email, phone_number, full_name, **extra_fields)

  def create_superuser(self, password,email=None, phone_number=None,full_name=None, **extra_fields):
    extra_fields.setdefault('is_superuser', True)
    extra_fields.setdefault('is_staff', True)
    extra_fields.setdefault('is_active', True)

    if extra_fields.get('is_superuser') is not True:
      raise ValueError('Superuser must have is_superuser=True.')

    return self._create_user(password, email, phone_number, full_name, **extra_fields)


class User(AbstractUser):
  full_name = models.CharField(blank=True, max_length=255, null=True)
  email = models.EmailField(blank=True, null=True, unique=True, db_index=True)
  phone_number = models.CharField(blank=True, null=True, unique=True, max_length=30)
  location=models.TextField(blank=True, null=True)

  is_active = models.BooleanField(default=False)
  otp = models.CharField(blank=True, null=True, max_length=4)
  otp_expires=models.DateTimeField(blank=True, null=True)
  is_verified = models.BooleanField(default=False)

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



