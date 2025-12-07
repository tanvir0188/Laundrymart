import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView

from message_utils.email_utils import send_otp_for_email_verification, send_otp_for_password, \
  send_otp_for_sms_password, send_otp_for_sms_verification
from .models import User
from .serializers import CreateUserSerializer, ForgetPasswordSerializer, LogoutSerializer, OTPSerializer, \
  ResendOTPSerializer, \
  ChangePasswordSerializer, MyTokenObtainPairSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny


class RegisterView(APIView):

  @extend_schema(
    request=CreateUserSerializer,
    responses={201: None, 400: 'Validation Error'}
  )
  def post(self, request):
    email = request.data.get('email')
    phone_number = request.data.get('phone_number')

    if not email and not phone_number:
      return Response(
        {"error": "Either email or phone number must be provided."},
        status=status.HTTP_400_BAD_REQUEST
      )

    with transaction.atomic():
      existing_user = None

      # Check for existing record by email or phone
      if email:
        existing_user = User.objects.filter(email=email).first()
      elif phone_number:
        existing_user = User.objects.filter(phone_number=phone_number).first()


      # Handle existing user
      if existing_user:
        if existing_user.is_active and existing_user.is_verified:
          identifier = email or phone_number
          return Response(
            {"error": f"{identifier}: An account with this identifier already exists and is active."},
            status=status.HTTP_400_BAD_REQUEST
          )
        # Delete inactive/unverified user
        existing_user.delete()

    # Proceed with serialization and user creation
    serializer = CreateUserSerializer(data=request.data)
    if serializer.is_valid():
      user = serializer.save()

      # Send OTP based on which identifier was used
      if user.email:
        send_otp_for_email_verification(user.email, user.otp)
        message = "OTP sent to email."
      elif user.phone_number:
        send_otp_for_sms_verification(user.phone_number, user.otp)
        message = "OTP sent to phone number."
      else:
        message = "OTP generated but no delivery method available."

      return Response({'message': message}, status=status.HTTP_201_CREATED)

    # Handle validation errors gracefully
    errors = serializer.errors
    field, messages = next(iter(errors.items()))
    readable_field = field.replace('_', ' ').capitalize()
    first_message = messages[0] if isinstance(messages, list) else messages
    error_message = f"{readable_field}: {first_message}"

    return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)



class VerifyOTPView(APIView):
  @extend_schema(
    request=OTPSerializer,
    responses={
      200: OpenApiResponse(description='OTP verified successfully with tokens'),
      400: OpenApiResponse(description='Invalid or expired OTP'),
      404: OpenApiResponse(description='User not found'),
    }
  )
  def patch(self, request):
    serializer = OTPSerializer(data=request.data)
    if not serializer.is_valid():
      errors = serializer.errors
      field, messages = next(iter(errors.items()))
      readable_field = field.replace('_', ' ').capitalize()
      first_message = messages[0] if isinstance(messages, list) else messages
      error_message = f"{readable_field}: {first_message}"
      return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data.get('email')
    phone_number = serializer.validated_data.get('phone_number')
    otp = serializer.validated_data.get('otp')

    # Find user by email or phone
    user = None
    if email:
      user = User.objects.filter(email=email).first()
    elif phone_number:
      user = User.objects.filter(phone_number=phone_number).first()

    if not user:
      return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check OTP validity
    if user.otp != otp:
      return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.otp_expires or user.otp_expires < timezone.now():
      return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)

    # Activate and verify user
    user.is_active = True
    user.is_verified = True
    user.otp = None
    user.otp_expires = None
    user.last_login = timezone.now()
    user.save(update_fields=['is_active', 'is_verified', 'otp', 'otp_expires', 'last_login'])

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    data = {
      'message': 'OTP verified successfully.',
      'access': str(access),
      'refresh': str(refresh),
      'login_user_info': {
        'name': user.full_name or f'{user.first_name} {user.last_name}'.strip(),
        'image': user.image.url if user.image else None
      }
    }

    return Response(data, status=status.HTTP_200_OK)

class ResendOTPView(APIView):
  @extend_schema(
    request=ResendOTPSerializer,
    responses={200: OpenApiResponse(description='OTP resent successfully'), 404: OpenApiResponse(description='Inactive user not found')}
  )
  def post(self, request):
    serializer = ResendOTPSerializer(data=request.data)
    if not serializer.is_valid():
      errors = serializer.errors
      field, messages = next(iter(errors.items()))
      readable_field = field.replace('_', ' ').capitalize()
      first_message = messages[0] if isinstance(messages, list) else messages
      error_message = f"{readable_field}: {first_message}"
      return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data.get('email')
    phone_number = serializer.validated_data.get('phone_number')

    with transaction.atomic():
      user = None
      if email:
        user = User.objects.filter(email=email, is_active=False).first()
      elif phone_number:
        user = User.objects.filter(phone_number=phone_number, is_active=False).first()

      if not user:
        return Response(
          {'error': 'Inactive user not found with that identifier.'},
          status=status.HTTP_404_NOT_FOUND
        )

      # Generate new OTP
      otp = random.randint(1000, 9999)
      otp_expiry = timezone.now() + timedelta(minutes=1)

      user.otp = str(otp)
      user.otp_expires = otp_expiry
      user.save(update_fields=['otp', 'otp_expires'])

      # Send OTP via correct channel
      if user.email:
        send_otp_for_email_verification(user.email, otp)
        message = 'OTP resent to email.'
      elif user.phone_number:
        send_otp_for_sms_verification(user.phone_number, otp)
        message = 'OTP resent to phone number.'
      else:
        message = 'OTP generated but no delivery method available.'

      return Response({'message': message}, status=status.HTTP_200_OK)

class ChangePasswordAPIView(APIView):
  permission_classes = [IsAuthenticated]


  @extend_schema(
    request=ChangePasswordSerializer,
    responses={200:None, 400: 'Validation Error'}
  )
  def patch(self, request):
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if not serializer.is_valid():
      errors = serializer.errors
      field, messages = next(iter(errors.items()))
      readable_field = field.replace('_', ' ').capitalize()
      first_message = messages[0] if isinstance(messages, list) else messages
      error_message = f"{readable_field}: {first_message}"
      return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    new_password = serializer.validated_data['new_password']

    user.set_password(new_password)
    user.save()

    return Response({'message': 'Password changed successfully.'}, status=200)

@extend_schema(
  request=ForgetPasswordSerializer,
  responses={200:None, 400: 'Validation Error'}
)
@api_view(['POST'])
@permission_classes([AllowAny])
def forget_password_otp(request):
  serializer = ForgetPasswordSerializer(data=request.data)
  if not serializer.is_valid():
    errors = serializer.errors
    field, messages = next(iter(errors.items()))
    readable_field = field.replace('_', ' ').capitalize()
    first_message = messages[0] if isinstance(messages, list) else messages
    error_message = f"{readable_field}: {first_message}"
    return Response({"error": error_message}, status=400)

  email = serializer.validated_data.get('email')
  phone_number = serializer.validated_data.get('phone_number')

  # Find user by email or phone
  user = None
  if email:
    user = User.objects.filter(email=email, is_active=True).first()
  elif phone_number:
    user = User.objects.filter(phone_number=phone_number, is_active=True).first()

  if not user:
    return Response({'error': 'User not found'}, status=404)

  # Generate OTP and expiry
  otp = random.randint(1000, 9999)
  user.otp = str(otp)
  user.otp_expires = timezone.now() + timedelta(minutes=1)
  user.save(update_fields=['otp', 'otp_expires'])

  # Send OTP via correct channel
  if user.email:
    send_otp_for_password(user.email, otp)
    message = 'OTP sent to email.'
  elif user.phone_number:
    send_otp_for_sms_password(user.phone_number, otp)
    message = 'OTP sent to phone number.'
  else:
    message = 'OTP generated but no delivery method available.'

  return Response({
    'message': message,
    'status': 'success'
  }, status=200)

class MyTokenObtainPairView(TokenObtainPairView):
  serializer_class = MyTokenObtainPairSerializer

class LogoutAPIView(APIView):
  permission_classes = [IsAuthenticated]

  @extend_schema(
    request=LogoutSerializer,
    responses={205: None, 400: 'Validation Error'}
  )
  def post(self, request):
    serializer = LogoutSerializer(data=request.data)
    if serializer.is_valid():
      refresh_token = serializer.validated_data['refresh_token']
      try:
        RefreshToken(refresh_token).blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_205_RESET_CONTENT)
      except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    errors = serializer.errors
    field, messages = next(iter(errors.items()))
    readable_field = field.replace('_', ' ').capitalize()
    first_message = messages[0] if isinstance(messages, list) else messages
    error_message = f"{readable_field}: {first_message}"
    return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

