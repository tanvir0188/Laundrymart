from django.contrib import admin

from messaging.models import Message, Notification, Room, VendorNotification

# Register your models here.
admin.site.register(Message)
admin.site.register(Room)
admin.site.register(Notification)
admin.site.register(VendorNotification)