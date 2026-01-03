from django.urls import path

from payment.views import stripe_cancel, stripe_success

urlpatterns = [
  path("payment/success/", stripe_success, name="stripe_success"),
  path("payment/cancel/", stripe_cancel, name="stripe_cancel"),
]
