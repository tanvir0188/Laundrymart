from django.urls import path

from vendor.views import AcceptOrRejectQuoteAPIView, DashboardAPIView

urlpatterns = [
  path('accept-reject', AcceptOrRejectQuoteAPIView.as_view(), name='accept-reject'),
  path('dashboard', DashboardAPIView.as_view(), name='dashboard'),
]