from django.contrib import admin
from apps.core.tenants.models import Tenant, Property

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'custom_domain', 'status', 'created_at')
    search_fields = ('name', 'subdomain', 'custom_domain')
    list_filter = ('status',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'property_type', 'city', 'country', 'is_active')
    search_fields = ('name', 'city', 'country')
    list_filter = ('property_type', 'is_active', 'tenant')
