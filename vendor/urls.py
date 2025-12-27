from django.urls import path

from vendor.views import AcceptOrRejectQuoteAPIView

urlpatterns = [
  path('accept-reject', AcceptOrRejectQuoteAPIView.as_view(), name='accept-reject'),
]