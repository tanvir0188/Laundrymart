import os

import requests
from django.shortcuts import render
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from laundrymart.permissions import IsCustomer
from uber.cache_access_token import UBER_BASE_URL, uber_headers
from uber.serializers import UberCreateQuoteSerializer


# Create your views here.
class UberCreateQuoteAPIView(APIView):
  permission_classes = [IsCustomer]

  @extend_schema(
    request=UberCreateQuoteSerializer,
    responses={
      200: OpenApiResponse(
        description="Uber delivery quote created",
        response={
          "type": "object",
          "properties": {

          }
        }
      )
    }
  )
  def post(self, request):
    serializer = UberCreateQuoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    customer_id=os.getenv('UBER_CUSTOMER_ID')

    resp = requests.post(
      f"{UBER_BASE_URL}/customers/{customer_id}/delivery_quotes",
      headers=uber_headers(),
      json=serializer.to_uber_payload(),
      timeout=10,
    )
    # resp.raise_for_status()

    uber_data = resp.json()

    return Response(uber_data)