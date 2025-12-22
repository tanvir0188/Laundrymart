import random
from faker import Faker
from django.utils import timezone
from datetime import time
from accounts.models import User  # adjust app name if needed

fake = Faker()

PASSWORD = "arnob0188"

# Dhaka-ish coordinate bounds (real, usable)
LAT_RANGE = (23.70, 23.90)
LNG_RANGE = (90.35, 90.50)

def random_lat_lng():
  return (
    round(random.uniform(*LAT_RANGE), 6),
    round(random.uniform(*LNG_RANGE), 6),
  )

def create_customer():
  lat, lng = random_lat_lng()

  user = User.objects.create_user(
    email=fake.unique.email(),
    password=PASSWORD,
    full_name=fake.name(),
    is_active=True,
    is_verified=True,
    is_staff=False,
    location=fake.address(),
    lat=str(lat),
    lng=str(lng),
  )
  return user
from decimal import Decimal, ROUND_HALF_UP
def d(value):
  return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def create_vendor():
  lat, lng = random_lat_lng()

  user = User.objects.create_user(
    email=fake.unique.email(),
    password=PASSWORD,
    full_name=fake.company(),
    is_active=True,
    is_verified=True,
    is_staff=True,
    laundrymart_name=fake.company(),
    location=fake.address(),
    lat=str(lat),
    lng=str(lng),

    price_per_pound=d(random.uniform(1.5, 4.5)),
    service_fee=d(random.uniform(1, 3)),

    minimum_order_weight=d(random.uniform(3, 10)),
    daily_capacity_limit=d(random.uniform(50, 150)),

    # Turnaround times (hours)
    turnaround_time_minimum_monday=12,
    turnaround_time_maximum_monday=24,
    turnaround_time_minimum_tuesday=12,
    turnaround_time_maximum_tuesday=24,
    turnaround_time_minimum_wednesday=12,
    turnaround_time_maximum_wednesday=24,
    turnaround_time_minimum_thursday=12,
    turnaround_time_maximum_thursday=24,
    turnaround_time_minimum_friday=12,
    turnaround_time_maximum_friday=24,
    turnaround_time_minimum_saturday=12,
    turnaround_time_maximum_saturday=24,
    turnaround_time_minimum_sunday=12,
    turnaround_time_maximum_sunday=24,

    # Operating hours
    operating_hours_start_monday=time(9, 0),
    operating_hours_end_monday=time(21, 0),
    operating_hours_start_tuesday=time(9, 0),
    operating_hours_end_tuesday=time(21, 0),
    operating_hours_start_wednesday=time(9, 0),
    operating_hours_end_wednesday=time(21, 0),
    operating_hours_start_thursday=time(9, 0),
    operating_hours_end_thursday=time(21, 0),
    operating_hours_start_friday=time(9, 0),
    operating_hours_end_friday=time(21, 0),
    operating_hours_start_saturday=time(10, 0),
    operating_hours_end_saturday=time(20, 0),
    operating_hours_start_sunday=time(10, 0),
    operating_hours_end_sunday=time(18, 0),
  )
  return user

def run():
  customers = 0
  vendors = 0

  for _ in range(50):
    create_customer()
    customers += 1

  for _ in range(50):
    create_vendor()
    vendors += 1

  print(f"Created {customers} customers and {vendors} vendors.")

run()
