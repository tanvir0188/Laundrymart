from django.contrib import admin

from customer.models import OrderReport, Review, OrderReportImage

# Register your models here.
admin.site.register(Review)
admin.site.register(OrderReport)
admin.site.register(OrderReportImage)
