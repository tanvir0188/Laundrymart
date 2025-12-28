from django.db.models.signals import post_save
from django.dispatch import receiver

from payment.models import Order


@receiver(post_save, sender=Order)
def create_order_room(sender, instance, created, **kwargs):
  if created:
    from messaging.models import Room
    room = Room.objects.create(order=instance, name=f"Order-{instance.id}-Room")
    room.participants.add(instance.user)
    if instance.service_provider:
      room.participants.add(instance.service_provider)
    room.save()