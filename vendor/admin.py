from django.contrib import admin

from vendor.models import OrderReport, OrderReportImage

# Register your models here.
admin.site.register(OrderReportImage)
admin.site.register(OrderReport)