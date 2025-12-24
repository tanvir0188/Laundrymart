from django.contrib import admin

from uber.models import Delivery, DeliveryQuote, ManifestItem

# Register your models here.
admin.site.register(Delivery)
admin.site.register(DeliveryQuote)
admin.site.register(ManifestItem)
