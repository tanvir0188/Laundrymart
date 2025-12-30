from django.db.models import Avg, FloatField, Value
from django.db.models.expressions import RawSQL
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.template.context_processors import request
from django_filters import CharFilter, ChoiceFilter, FilterSet, NumberFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.contrib import django_filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from common_utils.distance_utils import calculate_distance_miles, calculate_distance_sql, get_best_location
from customer.serializers import ReviewSerializer, VendorSerializer
from laundrymart.permissions import IsCustomer

class VendorPagination(PageNumberPagination):
  page_size = 10
  page_size_query_param = 'page_size'
  max_page_size = 50

# Create your views here.
class VendorAPIView(ListAPIView):
  serializer_class = VendorSerializer
  permission_classes = [IsCustomer]
  pagination_class = VendorPagination
  filter_backends = [SearchFilter, OrderingFilter]

  search_fields = ['laundrymart_name','location']

  ordering_fields = ['average_rating','price_per_pound','distance']

  ordering = ['distance']  # default

  @extend_schema(
    parameters=[
      OpenApiParameter(
        name='lat',
        description='Latitude to calculate distance',
        required=False,
        type=float
      ),
      OpenApiParameter(
        name='lng',
        description='Longitude to calculate distance',
        required=False,
        type=float

      ),
    ]
  )
  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)
  def get_queryset(self):
    user = self.request.user

    try:
      lat = float(self.request.query_params.get('lat', user.lat))
      lng = float(self.request.query_params.get('lng', user.lng))
    except (TypeError, ValueError):
      # fallback if user.lat or user.lng is None
      lat = None
      lng = None

    qs = User.objects.filter(
      is_staff=True,
      is_superuser=False
    ).annotate(
      average_rating=Coalesce(
        Avg('received_reviews__rating', output_field=FloatField()),
        Value(0.0)
      )
    )

    if lat is not None and lng is not None:
      qs = qs.annotate(
        distance=calculate_distance_sql(lat, lng)
      )

    return qs

class ChooseForCustomer(APIView):
  """
  API endpoint that automatically selects the cheapest LaundryMart (vendor)
  within a 10-mile radius of the customer's saved location (user.lat / user.lng).

  - Uses the customer's saved lat/lng directly (no query params needed)
  - Uses your existing calculate_distance_sql function for distance calculation
  - Prioritizes lowest price_per_pound among vendors with valid price and coordinates
  - Returns 404 if no vendor found within 10 miles
  """
  permission_classes = [IsCustomer]

  def get(self, request):
    customer = request.user

    # Use customer's saved coordinates directly
    if not customer.lat or not customer.lng:
      return Response(
        {"detail": "Customer location (lat/lng) is not saved in profile."},
        status=status.HTTP_400_BAD_REQUEST
      )

    try:
      lat = float(customer.lat)
      lng = float(customer.lng)
    except (ValueError, TypeError):
      return Response(
        {"detail": "Invalid latitude or longitude in customer profile."},
        status=status.HTTP_400_BAD_REQUEST
      )

    # Optimized single query using your existing calculate_distance_sql
    candidates = (
      User.objects.filter(
        is_staff=True,
        is_superuser=False,
        price_per_pound__isnull=False,
        lat__isnull=False,
        lng__isnull=False,
      )
      .annotate(distance=calculate_distance_sql(lat, lng))
      .filter(distance__lte=10)  # within 10 miles
      .order_by('price_per_pound')  # lowest price first
    )

    if not candidates.exists():
      return Response(
        {"detail": "No LaundryMart found within 10 miles with available pricing."},
        status=status.HTTP_404_NOT_FOUND
      )

    selected_vendor = candidates.first()
    serializer = VendorSerializer(selected_vendor)

    return Response(serializer.data, status=status.HTTP_200_OK)

class ReviewAPIView(APIView):
  permission_classes = [IsCustomer]

  @extend_schema(
    request=ReviewSerializer,
    responses={201: None, 400: 'Validation Error'}
  )
  def post(self, request, pk):
    user = request.user
    vendor=User.objects.get(pk=pk)
    serializer = ReviewSerializer(data=request.data)
    try:
      if serializer.is_valid():
        serializer.save(user=user, vendor=vendor)
        return Response({'message':'Review has been given'}, status=status.HTTP_201_CREATED)
      errors = serializer.errors
      field, messages = next(iter(errors.items()))
      readable_field = field.replace('_', ' ').capitalize()
      first_message = messages[0] if isinstance(messages, list) else messages
      error_message = f"{readable_field}: {first_message}"
      return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
      return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def list_saved_cards(request):
#   """List all saved payment methods for this user"""
#   try:
#     payment_methods = SavedPaymentMethod.objects.filter(user=request.user)
#
#     cards = [{
#       'id': pm.stripe_payment_method_id,
#       'brand': pm.card_brand,
#       'last4': pm.last4,
#       'exp_month': pm.exp_month,
#       'exp_year': pm.exp_year,
#       'is_default': pm.is_default
#     } for pm in payment_methods]
#
#     return Response({
#       'success': True,
#       'has_cards': len(cards) > 0,
#       'cards': cards
#     })
#
#   except Exception as e:
#     return Response({
#       'success': False,
#       'error': str(e)
#     }, status=400)