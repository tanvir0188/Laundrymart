# payments/utils.py
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_customer(user):
  """Create Stripe Customer if not exists"""
  if not user.orders.filter(stripe_customer_id__isnull=False).exists():
    customer = stripe.Customer.create(
      email=user.email or None,
      name=user.full_name or None,
      metadata={'django_user_id': user.id}
    )
    # You could add a field on User if you want one customer per user
    return customer.id
  # Reuse existing from any order
  return user.orders.exclude(stripe_customer_id__isnull=True).first().stripe_customer_id

def create_setup_checkout_session(order, success_url, cancel_url):
  """
  Create Checkout Session in setup mode (zero charge, saves card)
  """
  session = stripe.checkout.Session.create(
    mode="setup",
    customer=order.stripe_customer_id,
    payment_method_types=["card"],
    success_url=success_url,
    cancel_url=cancel_url,
    metadata={'order_uuid': str(order.uuid)},
  )
  return session