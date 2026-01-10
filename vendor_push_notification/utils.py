from messaging.models import VendorNotification

def vendor_create_notification(recipient,category, message, target_url=None, additional_info=None):
  VendorNotification.objects.create(
      recipient=recipient,
      category=category,
      text=message,
      target_url=target_url,
      additional_info=additional_info
  )

def vendor_accept_or_reject_notification(delivery_quote, laundrymart):
  print(f'notification sent to {laundrymart.laundrymart_name}')