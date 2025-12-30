# payments/utils.py
import stripe
from django.conf import settings

from payment.models import SavedPaymentMethod

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_customer(user):
  """Create Stripe Customer if not exists in User model"""
  # Check if user already has a Stripe customer ID
  if not user.stripe_customer_id:
    try:
      # Create a new customer in Stripe
      customer = stripe.Customer.create(
        email=user.email or None,
        name=user.full_nameZ,  # Assuming Django's User model
        metadata={'django_user_id': user.id}
      )
      user.stripe_customer_id = customer.id
      user.save()

      return customer.id

    except Exception as e:
      # Log the error
      print(f"Error creating Stripe customer: {str(e)}")
      return None

  return user.stripe_customer_id

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

def sync_payment_method(user, payment_method_id):
    """Save payment method reference to database"""
    import stripe
    from django.conf import settings

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
      # Retrieve the payment method details from Stripe
      pm = stripe.PaymentMethod.retrieve(payment_method_id)

      # Check if this payment method already exists in our DB
      existing = SavedPaymentMethod.objects.filter(
        user=user,
        stripe_payment_method_id=payment_method_id
      ).first()

      if existing:
        # Update the existing record
        existing.last4 = pm.card.last4
        existing.card_brand = pm.card.brand
        existing.exp_month = pm.card.exp_month
        existing.exp_year = pm.card.exp_year
        existing.save()
        return existing

      # Create a new record
      payment_method = SavedPaymentMethod.objects.create(
        user=user,
        stripe_payment_method_id=payment_method_id,
        last4=pm.card.last4,
        card_brand=pm.card.brand,
        exp_month=pm.card.exp_month,
        exp_year=pm.card.exp_year,
        # If this is the user's first payment method, make it the default
        is_default=not SavedPaymentMethod.objects.filter(user=user).exists()
      )

      return payment_method

    except Exception as e:
      print(f"Error syncing payment method: {str(e)}")
      return None