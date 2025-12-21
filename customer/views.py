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

  def get_queryset(self):
    user = self.request.user

    qs = User.objects.filter(
      is_staff=True,
      is_superuser=False
    ).annotate(
      average_rating=Coalesce(
        Avg('received_reviews__rating', output_field=FloatField()),
        Value(0.0)
      )
    )

    if user.lat and user.lng:
      qs = qs.annotate(
        distance=calculate_distance_sql(user.lat, user.lng)
      )

    return qs

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
