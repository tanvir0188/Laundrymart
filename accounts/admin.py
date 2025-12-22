from django.contrib import admin
from .models import Service, User
# Register your models here.

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'is_staff', 'is_active')
    search_fields = ('email', 'full_name')
    
admin.site.register(User, UserAdmin)

admin.site.register(Service)