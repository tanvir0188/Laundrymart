from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
import random

class CreateUserSerializer(serializers.ModelSerializer):
  role = serializers.ChoiceField(choices=['Customer', 'Vendor'], write_only=True)
  class Meta:
    model = User
    fields = ['email', 'phone_number', 'role', 'password']
    extra_kwargs = {'password': {'write_only': True}}

  def validate(self, attrs):
    email = attrs.get('email')
    phone_number = attrs.get('phone_number')
    role = attrs.get('role')
    if role not in ['Customer', 'Vendor']:
      raise serializers.ValidationError({"role": "Role must be either 'Customer' or 'Vendor'."})


    if not email and not phone_number:
      raise serializers.ValidationError("Either email or phone number must be provided.")

    # Validate email if present
    if email:
      try:
        validate_email(email)
      except ValidationError:
        raise serializers.ValidationError({"email": "Enter a valid email address."})

      if User.objects.filter(email=email).exists():
        raise serializers.ValidationError({"email": "An account with this email already exists."})

      if User.objects.filter(phone_number=phone_number).exists():
        raise serializers.ValidationError({"phone_number": "An account with this phone number already exists."})

    # Validate password
    password = attrs.get('password')
    if password:
      try:
        validate_password(password)
      except ValidationError as e:
        raise serializers.ValidationError({"password": list(e.messages)})

    return attrs

  def create(self, validated_data):
    email = validated_data.get('email')
    phone_number = validated_data.get('phone_number')
    role = validated_data.get('role')

    password = validated_data.pop('password')

    # generate OTP and expiry
    otp = random.randint(1000, 9999)
    otp_expiry = timezone.now() + timedelta(minutes=1)

    # Check if existing inactive user
    existing_user = User.objects.filter(
      Q(email=email) | Q(phone_number=phone_number)
    ).first()

    if existing_user:
      if existing_user.is_active:
        raise serializers.ValidationError("User already exists and is active.")

      existing_user.otp = str(otp)
      existing_user.otp_expires = otp_expiry
      existing_user.set_password(password)
      existing_user.save()
      return existing_user

    # Create a new user
    user = User(
      email=email,
      phone_number=phone_number,
      is_active=False,
      is_verified=False,
      otp=str(otp),
      otp_expires=otp_expiry,
      is_staff=False if role == 'Customer' else True,
    )
    user.set_password(password)
    user.save()
    return user

class ResendOTPSerializer(serializers.Serializer):
  email = serializers.EmailField(required=False, allow_null=True)
  phone_number = serializers.CharField(required=False, allow_null=True, max_length=30)

  def validate(self, attrs):
    email = attrs.get('email')
    phone_number = attrs.get('phone_number')
    if not email and not phone_number:
      raise serializers.ValidationError("Either email or phone number must be provided.")
    return attrs

class ForgetPasswordSerializer(serializers.Serializer):
  email = serializers.EmailField(required=False, allow_null=True)
  phone_number = serializers.CharField(required=False, allow_null=True, max_length=30)

  def validate(self, attrs):
    email = attrs.get('email')
    phone_number = attrs.get('phone_number')
    if not email and not phone_number:
      raise serializers.ValidationError("Either email or phone number must be provided.")
    return attrs

class ChangePasswordSerializer(serializers.Serializer):
  new_password = serializers.CharField(required=True)

  def validate_new_password(self, value):
    # Use Django’s built-in password validators
    try:
      validate_password(value)
    except ValidationError as e:
      raise serializers.ValidationError(e.messages)
    return value

from rest_framework import serializers

class OTPSerializer(serializers.Serializer):
  email = serializers.EmailField(required=False, allow_null=True)
  phone_number = serializers.CharField(required=False, allow_null=True, max_length=30)
  otp = serializers.CharField(max_length=4)

  def validate(self, attrs):
    email = attrs.get('email')
    phone_number = attrs.get('phone_number')
    otp = attrs.get('otp')

    if not email and not phone_number:
      raise serializers.ValidationError("Either email or phone number must be provided.")
    if not otp:
      raise serializers.ValidationError("OTP is required.")
    return attrs


# class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
#   def validate(self, attrs):
#     data = super().validate(attrs)
#
#     user = self.user
#
#     # Prepare extra user info (outside token)
#     data['login_user_info'] = {
#       'name': user.full_name if user.full_name else '',
#       'image': user.image.url if user.image else None
#     }
#     return data


class LogoutSerializer(serializers.Serializer):
  refresh_token = serializers.CharField(required=True)

class CustomerProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['id', 'full_name', 'email', 'phone_number', 'image', 'location', 'lat', 'lng']

class VendorProfileSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['id', 'full_name', 'email', 'phone_number', 'image', 'location', 'lat', 'lng',
              'laundrymart_name', 'price_per_pound', 'service_fee', 'minimum_order_weight',
              'daily_capacity_limit',
              'turnaround_time_minimum_sunday', 'turnaround_time_maximum_sunday',
              'turnaround_time_minimum_monday', 'turnaround_time_maximum_monday',
              'turnaround_time_minimum_tuesday', 'turnaround_time_maximum_tuesday',
              'turnaround_time_minimum_wednesday', 'turnaround_time_maximum_wednesday',
              'turnaround_time_minimum_thursday', 'turnaround_time_maximum_thursday',
              'turnaround_time_minimum_friday', 'turnaround_time_maximum_friday',
              'turnaround_time_minimum_saturday', 'turnaround_time_maximum_saturday',

              'operating_hours_start_sunday', 'operating_hours_end_sunday', 'is_closed_sunday',
              'operating_hours_start_monday', 'operating_hours_end_monday', 'is_closed_monday',
              'operating_hours_start_tuesday', 'operating_hours_end_tuesday', 'is_closed_tuesday',
              'operating_hours_start_wednesday', 'operating_hours_end_wednesday', 'is_closed_wednesday',
              'operating_hours_start_thursday', 'operating_hours_end_thursday', 'is_closed_thursday',
              'operating_hours_start_friday', 'operating_hours_end_friday', 'is_closed_friday',
              'operating_hours_start_saturday', 'operating_hours_end_saturday', 'is_closed_saturday'
              ]

class VendorSettingSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['push_and_email_alerts', 'auto_accept_orders']

class CustomerSettingSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ['push_and_email_alerts', 'preference']