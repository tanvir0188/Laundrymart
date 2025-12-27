from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from laundrymart.permissions import IsStaff
from uber.models import DeliveryQuote


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