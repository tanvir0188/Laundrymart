from django.urls import path

from vendor.views import AcceptOrRejectQuoteAPIView, DashboardAPIView, VendorOrderReportAPIView, VendorOrdersListAPIView

urlpatterns = [
  path('accept-reject', AcceptOrRejectQuoteAPIView.as_view(), name='accept-reject'),
  path('dashboard', DashboardAPIView.as_view(), name='dashboard'),
  path('order-list', VendorOrdersListAPIView.as_view(), name='order-list'),
  path('order-report', VendorOrderReportAPIView.as_view(), name='order-list'),
]