from messaging.models import CustomerNotification


def customer_create_notification(recipient,category, message, target_url=None, additional_info=None):
  CustomerNotification.objects.create(
      recipient=recipient,
      category=category,
      text=message,
      target_url=target_url,
      additional_info=additional_info
  )