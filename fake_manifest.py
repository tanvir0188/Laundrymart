import random

from fake_data import d, fake
from uber.models import BAG_CHOICES, Delivery, ManifestItem  # Adjust to your app's import path

def generate_fake_manifest_item():
    # Random delivery
    delivery = Delivery.objects.order_by('?').first()  # Get a random delivery from the DB

    # Randomize bag size
    bag_size = random.choice([x[0] for x in BAG_CHOICES])

    # Generate random weight and price
    weight = d(random.uniform(0.5, 10.0))
    price = d(random.uniform(5.0, 50.0))

    manifest_item = ManifestItem.objects.create(
        delivery=delivery,
        name=fake.word(),
        quantity=random.randint(1, 5),
        size=bag_size,
        weight=weight,
        price=price,
        vat_percentage=d(random.uniform(5.0, 20.0)),
        dimensions={"length": random.randint(10, 50), "width": random.randint(10, 50), "height": random.randint(10, 50)}
    )
    return manifest_item

# Generate 50 fake manifest items
for _ in range(50):
    generate_fake_manifest_item()
