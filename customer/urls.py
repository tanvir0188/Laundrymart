from django.urls import path

from uber.views import UberCreateQuoteAPIView
from . import views
urlpatterns = [
  path('vendors', views.VendorAPIView.as_view(), name='vendors'),
  path('review/<int:pk>', views.ReviewAPIView.as_view(), name='reviews'),
  path('get-quote', UberCreateQuoteAPIView.as_view(), name='get-quote'),
]