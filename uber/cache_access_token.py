# utils/uber.py or services/uber_client.py
import requests
from laundrymart import settings
from django.core.cache import cache
from django.utils import timezone

UBER_TOKEN_CACHE_KEY = 'uber_direct:access_token'  # prefixed for clarity
UBER_TOKEN_EXPIRES_MARGIN = 86400  # Refresh 1 day before expiry (safe for 30-day tokens)


def get_uber_access_token():
  """
  Get cached Uber Direct access token, refresh if missing or about to expire.
  Works perfectly with Redis cache across all workers.
  """
  token_data = cache.get(UBER_TOKEN_CACHE_KEY)

  if token_data and token_data.get('expires_at', timezone.now()) > timezone.now():
    return token_data['access_token']

  # Fetch new token from Uber
  response = requests.post(
    'https://auth.uber.com/oauth/v2/token',
    data={
      'client_id': settings.UBER_CLIENT_ID,
      'client_secret': settings.UBER_CLIENT_SECRET,
      'grant_type': 'client_credentials',
      'scope': 'eats.deliveries',
    },
    timeout=10
  )
  response.raise_for_status()
  data = response.json()

  # Store with expiry info
  expires_at = timezone.now() + timezone.timedelta(seconds=data.get('expires_in', 2592000))
  cached_data = {
    'access_token': data['access_token'],
    'expires_at': expires_at,
  }

  # Cache for slightly less than actual expiry
  cache_ttl = data.get('expires_in', 2592000) - UBER_TOKEN_EXPIRES_MARGIN
  cache.set(UBER_TOKEN_CACHE_KEY, cached_data, timeout=cache_ttl)

  return data['access_token']