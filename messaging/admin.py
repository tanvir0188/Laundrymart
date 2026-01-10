from django.contrib import admin

from messaging.models import Message,CustomerNotification, Room, VendorNotification

# Register your models here.
admin.site.register(Message)
admin.site.register(Room)
admin.site.register(CustomerNotification)
admin.site.register(VendorNotification)