from django.contrib import admin

from payment.models import Order, Payment

# Register your models here.
admin.site.register(Payment)
admin.site.register(Order)