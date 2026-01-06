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
  page_size = 20
  page_size_query_param = 'page_size'
  max_page_size = 100

class VendorOrdersListAPIView(APIView):
  permission_classes = [IsStaff]
  pagination_class = StandardResultsSetPagination

  def get(self, request):
    filter_type = request.query_params.get('filter', 'delivered').lower()

    user = request.user
    # Adjust this based on how LaundrymartStore is linked to User
    # Example: assuming OneToOne or ForeignKey from User to LaundrymartStore
    try:
      # Replace with your actual relation, e.g.:
      # store = user.laundry_store  # or user.laundry_mart_store
      # For now assuming a field on User: laundrymart_name + external_store_id logic
      # Common pattern: User has a related LaundrymartStore
      store = user.laundrymart_store  # ← CHANGE THIS to your actual relation
      external_store_id = store.store_id  # field that matches Uber's external_store_id
    except AttributeError:
      return Response({"error": "Laundrymart store not linked to this user"}, status=400)

    # We'll collect unified results with a creation timestamp for sorting
    results = []

    if filter_type == 'pending':
      # Pending quotes: DeliveryQuote with status='pending'
      quotes_qs = DeliveryQuote.objects.filter(
        external_store_id=external_store_id,
        status='pending'
      ).select_related('customer').prefetch_related('manifest_items').order_by('-saved_at')

      paginator = self.pagination_class()
      page = paginator.paginate_queryset(quotes_qs, request)

      for quote in page:
        time_ago = humanize.naturaltime(timezone.now() - quote.saved_at)

        results.append({
          "id": None,
          "order_id": quote.quote_id,
          "phone_number": quote.dropoff_phone_number or quote.pickup_phone_number,
          "time_ago": time_ago,
          "user": quote.customer.full_name or quote.customer.phone_number or quote.customer.email,
          "service_provider": user.laundrymart_store.laundrymart_name or user.full_name,
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

      ).select_related('user', 'service_provider').prefetch_related('manifest_items').order_by('-created_at')

      paginator = self.pagination_class()

      page = paginator.paginate_queryset(orders_qs, request)

      if page is None:
        return Response({"error": "Pagination error"}, status=400)

      results = []

      for order in page:
        time_ago = humanize.naturaltime(timezone.now() - order.created_at)

        # Use your existing serializer

        serialized = OrderDetailSerializer(order).data

        # Override/enhance fields as needed

        serialized.update({

          "id": order.id,  # keep pk if frontend uses it

          "order_id": str(order.uuid),  # This is what you want: UUID shown as order_id

          "time_ago": time_ago,

          "vendor_fee": order.delivery_fee_cents / Decimal('100') if order.delivery_fee_cents else None,

          "address": serialized.get('address') or order.dropoff_address or order.pickup_address,

          "is_quote": False,

          "created_at": order.created_at.isoformat(),

        })

        results.append(serialized)

    else:
      return Response({"error": "Invalid filter. Use: pending, active, delivered"}, status=400)

    # Apply pagination response structure
    return paginator.get_paginated_response({
      "results": results,
      "filter": filter_type,
    })

