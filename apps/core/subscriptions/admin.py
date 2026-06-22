from django.contrib import admin
from apps.core.subscriptions.models import (
    Product, SubscriptionPlan, SubscriptionPlanProduct, SubscriptionEntitlement, TenantSubscription,
    ProductFeature, TenantProduct, TenantProductLicense, TenantProductEntitlement, TenantProductUsage
)

class SubscriptionPlanProductInline(admin.TabularInline):
    model = SubscriptionPlanProduct
    extra = 1

class SubscriptionEntitlementInline(admin.TabularInline):
    model = SubscriptionEntitlement
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'billing_cycle', 'price', 'currency', 'is_active')
    search_fields = ('name',)
    inlines = [SubscriptionPlanProductInline, SubscriptionEntitlementInline]

@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'plan', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'plan')
    search_fields = ('tenant__name',)

@admin.register(ProductFeature)
class ProductFeatureAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'product', 'tenant', 'is_active')
    list_filter = ('product', 'is_active', 'tenant')
    search_fields = ('code', 'name')

@admin.register(TenantProduct)
class TenantProductAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'product', 'tenant_subscription', 'activated_at', 'expires_at', 'status')
    list_filter = ('status', 'product')
    search_fields = ('tenant__name', 'product__code')

@admin.register(TenantProductLicense)
class TenantProductLicenseAdmin(admin.ModelAdmin):
    list_display = ('license_key', 'tenant_product', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
    search_fields = ('license_key', 'tenant_product__tenant__name')

@admin.register(TenantProductEntitlement)
class TenantProductEntitlementAdmin(admin.ModelAdmin):
    list_display = ('tenant_product', 'feature_code', 'limit_type', 'limit_value_boolean', 'limit_value_numeric')
    list_filter = ('limit_type', 'feature_code')
    search_fields = ('feature_code', 'tenant_product__tenant__name')

@admin.register(TenantProductUsage)
class TenantProductUsageAdmin(admin.ModelAdmin):
    list_display = ('tenant_product', 'metric_code', 'usage_value', 'usage_limit', 'percentage_used', 'last_calculated_at')
    list_filter = ('metric_code',)
    search_fields = ('metric_code', 'tenant_product__tenant__name')

