from django.contrib import admin
from apps.features.availability.models import InventoryAvailability, InventoryRestriction, InventoryHold

@admin.register(InventoryAvailability)
class InventoryAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('property', 'inventory_unit_type', 'date', 'allocated_count', 'sold_count', 'blocked_count', 'overbooking_limit', 'tenant')
    list_filter = ('property', 'inventory_unit_type', 'date', 'tenant')
    search_fields = ('property__name', 'inventory_unit_type__name', 'inventory_unit_type__code')
    date_hierarchy = 'date'
    ordering = ('-date', 'property', 'inventory_unit_type')


@admin.register(InventoryRestriction)
class InventoryRestrictionAdmin(admin.ModelAdmin):
    list_display = ('property', 'inventory_unit_type', 'date', 'restriction_type', 'restriction_value', 'tenant')
    list_filter = ('property', 'inventory_unit_type', 'date', 'restriction_type', 'tenant')
    search_fields = ('property__name', 'inventory_unit_type__name', 'restriction_type')
    date_hierarchy = 'date'
    ordering = ('-date', 'property')


@admin.register(InventoryHold)
class InventoryHoldAdmin(admin.ModelAdmin):
    list_display = ('hold_type', 'inventory_unit_type', 'quantity', 'expires_at', 'status', 'property', 'tenant')
    list_filter = ('property', 'inventory_unit_type', 'status', 'hold_type', 'tenant')
    search_fields = ('property__name', 'inventory_unit_type__name', 'hold_type', 'status')
    ordering = ('-expires_at',)
