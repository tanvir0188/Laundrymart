import random
from datetime import datetime
from uuid import uuid4  # For generating unique UUIDs
from faker import Faker
from rest_framework.generics import get_object_or_404

from accounts.models import LaundrymartStore, User
from fake_data import d, random_lat_lng
from uber.models import Delivery, DeliveryQuote  # Adjust to your app's import path
from payment.models import Order  # Adjust to your app's import path

fake = Faker()

def create_fake_order():
    # Fetch a random delivery that is not already attached to an order
    delivery = Delivery.objects.exclude(
        quote_uid__isnull=False,
        delivery_uid__isnull=False
    ).order_by('?').first()

    if not delivery:
        print("No available deliveries to attach to the order.")
        return None

    # Extract user and service provider (LaundrymartStore) from the delivery
    customer = delivery.customer  # User associated with the delivery
    service_provider_store_id = delivery.external_store_id  # LaundrymartStore associated with the delivery
    service_provider = get_object_or_404(LaundrymartStore, store_id=service_provider_store_id)

    # Generate random values for the order (address, lat/lng, etc.)
    pickup_lat, pickup_lng = random_lat_lng()
    dropoff_lat, dropoff_lng = random_lat_lng()

    # Create a unique order UUID
    order_uuid = str(uuid4())

    # Randomize the status
    status = random.choice(['pending_setup', 'processing', 'card_saved', 'picked_up', 'weighed', 'charged', 'return_scheduled', 'completed', 'canceled'])

    # Create random pricing and weights
    weight_in_pounds = d(random.uniform(1.0, 20.0))  # Random weight
    service_charge_cents = random.randint(1000, 5000)  # Random service fee in cents
    delivery_fee_cents = random.randint(500, 2000)  # Random delivery fee in cents
    final_total_cents = service_charge_cents + delivery_fee_cents

    # Get the quote and delivery details from the existing delivery
    uber_pickup_quote_id = delivery.quote_uid
    uber_pickup_delivery_id = delivery.delivery_uid

    # Create the order
    order = Order.objects.create(
        uuid=order_uuid,
        user=customer,  # Use the user from the delivery
        service_provider=service_provider,  # Use the service provider (LaundrymartStore) from the delivery
        pickup_address=fake.address(),
        dropoff_address=fake.address(),
        pickup_latitude=pickup_lat,
        pickup_longitude=pickup_lng,
        dropoff_latitude=dropoff_lat,
        dropoff_longitude=dropoff_lng,
        uber_pickup_quote_id=uber_pickup_quote_id,
        uber_pickup_delivery_id=uber_pickup_delivery_id,
        weight_in_pounds=weight_in_pounds,
        service_charge_cents=service_charge_cents,
        delivery_fee_cents=delivery_fee_cents,
        final_total_cents=final_total_cents,
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    return order

# Generate 50 fake orders and attach random deliveries
for _ in range(50):
    create_fake_order()
