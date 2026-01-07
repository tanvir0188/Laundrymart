from datetime import timedelta
from decimal import Decimal

import humanize
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from laundrymart.permissions import IsStaff
from payment.models import Order
from uber.models import DeliveryQuote
from uber.serializers import ManifestItemSerializer
from vendor.serializers import DashboardSerializer, OrderDetailSerializer


class AcceptOrRejectQuoteAPIView(APIView):
  permission_classes = [IsStaff]
  def patch(self, request, quote_id):
    user=request.user
    external_store_id=user.store_id
    quote=get_object_or_404(DeliveryQuote, pk=quote_id)
    if external_store_id != quote.external_store_id:
      return Response({"error": "You do not have permission to modify this quote."}, status=status.HTTP_403_FORBIDDEN)
    action=request.data.get("action")
    if action not in ["accept", "reject"]:
      return Response({"error": "Invalid action. Must be 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)
    if action=="accept":
      quote.status="accepted"
      quote.save()
    elif action=="reject":
      quote.status="rejected"
      quote.save()
    return Response({
      "quote_id": quote.quote_id,
      "status": f'You have {quote.status} the quote.'
    }, status=status.HTTP_200_OK)

class DashboardAPIView(APIView):
  permission_classes = [IsStaff]

  def get(self, request):
    user = request.user
    print ("User:", user.email)
    associated_laundrymart = user.laundrymart_store
    current_month = timezone.now().month
    current_year = timezone.now().year
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    print("Associated Laundrymart:", associated_laundrymart)
    if not associated_laundrymart:
      return Response({"error": "No associated Laundrymart store found."}, status=status.HTTP_404_NOT_FOUND)
    store_uuid=associated_laundrymart.store_id
    context = {
      'request': request,
      'store_uuid': store_uuid,
      'associated_laundrymart': associated_laundrymart,
      'current_month': current_month,
      'current_year': current_year,
      'last_seven_days_start': seven_days_ago,
      'last_seven_days_end': today,
      }
    serializer = DashboardSerializer(user,context=context)
    print("Serialized Data:", serializer.data)
    return Response(serializer.data, status=status.HTTP_200_OK)

class StandardResultsSetPagination(PageNumberPagination):
  page_size = 10
  page_size_query_param = 'page_size'
  max_page_size = 100

class VendorOrdersListAPIView(APIView):
  permission_classes = [IsStaff]
  pagination_class = StandardResultsSetPagination

  def get(self, request):
    filter_type = request.query_params.get('filter', 'pending').lower()

    user = request.user

    try:

      store = user.laundrymart_store
      external_store_id = store.store_id
    except AttributeError:
      return Response({"error": "Laundrymart store not linked to this user"}, status=400)

    # We'll collect unified results with a creation timestamp for sorting
    results = []

    if filter_type == 'pending':
      quotes_qs = DeliveryQuote.objects.filter(
        external_store_id=external_store_id,
        status='pending'
      ).select_related('customer').prefetch_related('manifest_items').order_by('-saved_at')

      paginator = self.pagination_class()
      page = paginator.paginate_queryset(quotes_qs, request)
      if page is None:
        return Response({"error": "Pagination error"}, status=400)

      for quote in page:
        time_ago = humanize.naturaltime(timezone.now() - quote.saved_at)

        results.append({
          "id": None,
          "uuid": None,  # no UUID for quotes
          "order_id": None,  # frontend uses this as identifier
          "phone_number": quote.dropoff_phone_number or quote.pickup_phone_number,
          "time_ago": time_ago,
          "user": quote.customer.full_name or quote.customer.phone_number or quote.customer.email,
          # "service_provider": store.laundrymart_name or user.full_name,  # if needed
          "manifest_items": ManifestItemSerializer(quote.manifest_items.all(), many=True).data,
          "service": quote.service_type or "full_service",
          "total_cost": None,
          "vendor_fee": quote.fee / Decimal('100') if quote.fee else None,
          "address": quote.dropoff_address or quote.pickup_address,
          "is_quote": True,
          "quote_id": quote.quote_id,
          "expires": quote.expires.isoformat() if quote.expires else None,
          "created_at": quote.saved_at.isoformat(),
        })

    elif filter_type in ['active', 'delivered']:
      status_list = (
        ['card_saved', 'picked_up', 'weighed', 'charged', 'return_scheduled']
        if filter_type == 'active'
        else ['completed']
      )

      orders_qs = Order.objects.filter(
        service_provider=store,
        status__in=status_list
      ).select_related('user', 'service_provider').prefetch_related('manifest_items') \
        .order_by('-created_at')

      paginator = self.pagination_class()
      page = paginator.paginate_queryset(orders_qs, request)
      if page is None:
        return Response({"error": "Pagination error"}, status=400)

      for order in page:
        time_ago = humanize.naturaltime(timezone.now() - order.created_at)

        results.append({
          "id": order.id,
          "uuid": str(order.uuid),
          "order_id": str(order.uuid),  # consistent with frontend expectation
          "phone_number": order.user.phone_number or order.user.email,
          "time_ago": time_ago,
          "user": str(order.user),  # or order.user.full_name / email if you prefer
          # "service_provider": store.laundrymart_name,
          "manifest_items": ManifestItemSerializer(order.manifest_items.all(), many=True).data,
          "service": "full_service",  # or add a field later if needed
          "total_cost": order.final_total_cents / Decimal('100') if order.final_total_cents else None,
          "vendor_fee": order.delivery_fee_cents / Decimal('100') if order.delivery_fee_cents else None,
          "address": order.dropoff_address or order.pickup_address,
          "is_quote": False,
          "quote_id": None,
          "expires": None,
          "created_at": order.created_at.isoformat(),
        })

    else:
      return Response({"error": "Invalid filter. Use: pending, active, delivered"}, status=400)

    return paginator.get_paginated_response({
      "results": results,
      "filter": filter_type,
    })

