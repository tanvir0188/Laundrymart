import random
from datetime import datetime

from accounts.models import User
from fake_data import d, fake, random_lat_lng
from uber.models import Delivery, DeliveryQuote  # Adjust to your app's import path


def generate_fake_delivery():
    # Randomly select an existing delivery quote
    quote = DeliveryQuote.objects.order_by('?').first()  # Get a random delivery quote

    # If there are no existing quotes, we should handle this case
    if not quote:
        print("No delivery quote found. Skipping delivery creation.")
        return None

    # Generate random values for the delivery
    pickup_lat, pickup_lng = random_lat_lng()
    dropoff_lat, dropoff_lng = random_lat_lng()
    delivery_uid = fake.uuid4()

    # Generate random customer
    customer = User.objects.filter(is_staff=False).order_by('?').first()  # Get a random customer from the DB

    # Randomize the status
    status = random.choice(['pending', 'pickup_true', 'pickup_false', 'pickup_complete', 'dropoff_true', 'dropoff_false', 'delivered', 'canceled', 'returned'])

    # Generate a tracking URL
    tracking_url = f"https://tracking.uber.com/{delivery_uid}"

    # Random fee and currency
    fee = d(random.uniform(5.0, 50.0))
    total_fee = fee + d(random.uniform(2.0, 10.0))
    currency = "USD"

    # Create the delivery object and link it to the delivery quote
    delivery = Delivery.objects.create(
        delivery_uid=delivery_uid,
        quote=quote,  # Attach the random delivery quote
        customer=customer,
        status=status,
        fee=fee,
        total_fee=total_fee,
        currency=currency,
        tracking_url=tracking_url,
        pickup_latitude=pickup_lat,
        pickup_longitude=pickup_lng,
        dropoff_latitude=dropoff_lat,
        dropoff_longitude=dropoff_lng,
        created_at_uber=datetime.now(),
        updated_at_uber=datetime.now(),
    )
    return delivery


# Generate 50 fake deliveries
for _ in range(50):
    generate_fake_delivery()
