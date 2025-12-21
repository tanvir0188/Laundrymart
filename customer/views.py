from django.db.models import Avg, FloatField
from django.db.models.expressions import RawSQL
from django.shortcuts import render
from django_filters import CharFilter, ChoiceFilter, FilterSet, NumberFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.contrib import django_filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from common_utils.distance_utils import calculate_distance_miles, calculate_distance_sql, get_best_location
from customer.serializers import VendorSerializer
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
      average_rating=Avg(
        'received_reviews__rating',
        output_field=FloatField()
      )
    )

    if user.lat and user.lng:
      qs = qs.annotate(
        distance=calculate_distance_sql(user.lat, user.lng)
      )

    return qs
