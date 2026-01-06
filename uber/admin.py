from django.contrib import admin

from uber.models import Delivery, DeliveryQuote, ManifestItem

# Register your models here.
admin.site.register(Delivery)
class DeliveryQuoteAdmin(admin.ModelAdmin):
    list_display = ('quote_id', 'service_type', 'status', 'fee', 'currency', 'external_store_id',)
    search_fields = ('quote_id', 'external_store_id', 'customer__email')
admin.site.register(DeliveryQuote, DeliveryQuoteAdmin)
admin.site.register(ManifestItem)
