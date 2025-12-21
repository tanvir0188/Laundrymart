from django.urls import path
from . import views
urlpatterns = [
  path('vendors', views.VendorAPIView.as_view(), name='vendors'),
  path('review/<int:pk>', views.ReviewAPIView.as_view(), name='reviews'),
]