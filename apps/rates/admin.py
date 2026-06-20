from django.contrib import admin
from apps.rates.models import (
    MealPlan, CancellationPolicy, ChildPolicy, RatePlan,
    RatePlanInventoryType, RatePlanVersion, DerivedRateConfig,
    RateRuleOccupancy, RateRuleDayOfWeek, RateCalendar,
    PackageProduct, PackageProductRatePlan
)

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'price_adjustment', 'tax_percent', 'is_active', 'tenant')
    list_filter = ('is_active', 'tenant')
    search_fields = ('code', 'name')

@admin.register(CancellationPolicy)
class CancellationPolicyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'free_cancellation_hours', 'penalty_type', 'penalty_value', 'tenant')
    list_filter = ('penalty_type', 'tenant')
    search_fields = ('code', 'name')

@admin.register(ChildPolicy)
class ChildPolicyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'max_free_age', 'child_flat_charge', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('code', 'name')

@admin.register(RatePlan)
class RatePlanAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'property', 'category', 'is_derived', 'is_active', 'tenant')
    list_filter = ('category', 'is_derived', 'is_active', 'property', 'tenant')
    search_fields = ('code', 'name')

@admin.register(RatePlanInventoryType)
class RatePlanInventoryTypeAdmin(admin.ModelAdmin):
    list_display = ('rate_plan', 'inventory_unit_type', 'base_rate', 'tenant')
    list_filter = ('rate_plan__property', 'tenant')
    search_fields = ('rate_plan__code', 'inventory_unit_type__code')

@admin.register(RatePlanVersion)
class RatePlanVersionAdmin(admin.ModelAdmin):
    list_display = ('rate_plan', 'version_number', 'effective_from', 'effective_to')
    list_filter = ('rate_plan__property',)
    ordering = ('-effective_from',)

@admin.register(DerivedRateConfig)
class DerivedRateConfigAdmin(admin.ModelAdmin):
    list_display = ('child_rate_plan', 'anchor_rate_plan', 'modifier_type', 'modifier_value', 'tenant')
    list_filter = ('tenant',)

@admin.register(RateRuleOccupancy)
class RateRuleOccupancyAdmin(admin.ModelAdmin):
    list_display = ('rate_plan_inventory_type', 'occupancy_from', 'occupancy_to', 'modifier_type', 'value', 'tenant')
    list_filter = ('tenant',)

@admin.register(RateRuleDayOfWeek)
class RateRuleDayOfWeekAdmin(admin.ModelAdmin):
    list_display = ('rate_plan_inventory_type', 'day_of_week', 'modifier_type', 'value', 'tenant')
    list_filter = ('day_of_week', 'tenant')

@admin.register(RateCalendar)
class RateCalendarAdmin(admin.ModelAdmin):
    list_display = ('property', 'date', 'rate_plan', 'inventory_unit_type', 'amount', 'is_available')
    list_filter = ('property', 'date', 'rate_plan', 'inventory_unit_type', 'is_available')
    date_hierarchy = 'date'

@admin.register(PackageProduct)
class PackageProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'default_price', 'tax_percent', 'is_active', 'tenant')
    list_filter = ('category', 'is_active', 'tenant')
    search_fields = ('code', 'name')

@admin.register(PackageProductRatePlan)
class PackageProductRatePlanAdmin(admin.ModelAdmin):
    list_display = ('rate_plan', 'package_product', 'included_quantity', 'tenant')
    list_filter = ('tenant',)
