from django.urls import path

from accounts.views import SecondaryLocationAPIView, SecondaryLocationModifyAPIView
from uber.views import UberCreateQuoteAPIView
from . import views
from .views import ChooseForCustomer

urlpatterns = [
  path('vendors', views.VendorAPIView.as_view(), name='vendors'),
  path('review/<int:pk>', views.ReviewAPIView.as_view(), name='reviews'),
  path('get-quote', UberCreateQuoteAPIView.as_view(), name='get-quote'),
  path('locations', SecondaryLocationAPIView.as_view(), name='location'),
  path('location/<int:pk>', SecondaryLocationModifyAPIView.as_view(), name='location'),
  path('location', SecondaryLocationModifyAPIView.as_view(), name='location'),
  path('choose-for-customer', ChooseForCustomer.as_view(), name='choose-for-customer'),
]