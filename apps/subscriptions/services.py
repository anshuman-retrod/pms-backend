import logging
from django.utils import timezone
from decimal import Decimal
from django.db.models import F
from apps.subscriptions.models import (
    Product, ProductFeature, TenantProduct, TenantProductLicense, TenantProductEntitlement, TenantProductUsage
)
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

class ProductAccessService:
    @staticmethod
    def has_product(tenant, product_code):
        """
        Verify if a product is active for a given tenant.
        """
        if not tenant:
            return False
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        return TenantProduct.objects.filter(
            tenant_id=tenant_id,
            product__code=product_code,
            status='ACTIVE',
            tenant_subscription__status='ACTIVE',
            expires_at__gt=timezone.now()
        ).exists()

    @staticmethod
    def has_feature(tenant, feature_code):
        """
        Verify if a feature is active/entitled for a tenant.
        """
        if not tenant:
            return False
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        # Check if tenant has active product associated with this feature
        # And if there's a specific entitlement that overrides it
        entitlement = TenantProductEntitlement.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            tenant_product__tenant_subscription__status='ACTIVE',
            tenant_product__expires_at__gt=timezone.now(),
            feature_code=feature_code
        ).first()

        if entitlement:
            if entitlement.limit_type == 'BOOLEAN':
                return entitlement.limit_value_boolean
            elif entitlement.limit_type == 'NUMERIC':
                return entitlement.limit_value_numeric > 0 if entitlement.limit_value_numeric is not None else False
            return True

        # Fallback: check if the feature is registered under any active tenant product
        return ProductFeature.objects.filter(
            code=feature_code,
            is_active=True,
            product__tenant_products__tenant_id=tenant_id,
            product__tenant_products__status='ACTIVE',
            product__tenant_products__tenant_subscription__status='ACTIVE',
            product__tenant_products__expires_at__gt=timezone.now()
        ).exists()


class LicenseValidationService:
    @staticmethod
    def validate_license(license_key):
        """
        Validate license and update last_validated_at if valid.
        """
        try:
            license_obj = TenantProductLicense.objects.get(license_key=license_key)
        except TenantProductLicense.DoesNotExist:
            return False

        now = timezone.now()
        today = now.date()

        if license_obj.status != 'ACTIVE':
            return False

        if today < license_obj.start_date or today > license_obj.end_date:
            license_obj.status = 'EXPIRED'
            license_obj.save()
            return False

        license_obj.last_validated_at = now
        license_obj.save()
        return True

    @staticmethod
    def is_license_expired(license_key):
        try:
            license_obj = TenantProductLicense.objects.get(license_key=license_key)
        except TenantProductLicense.DoesNotExist:
            return True
        return license_obj.status == 'EXPIRED' or timezone.now().date() > license_obj.end_date

    @staticmethod
    def is_license_active(license_key):
        try:
            license_obj = TenantProductLicense.objects.get(license_key=license_key)
        except TenantProductLicense.DoesNotExist:
            return False
        today = timezone.now().date()
        return license_obj.status == 'ACTIVE' and license_obj.start_date <= today <= license_obj.end_date


class EntitlementValidationService:
    @staticmethod
    def get_limit(tenant, feature_code):
        """
        Get the limit value for a feature.
        """
        if not tenant:
            return None
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        entitlement = TenantProductEntitlement.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            tenant_product__tenant_subscription__status='ACTIVE',
            tenant_product__expires_at__gt=timezone.now(),
            feature_code=feature_code
        ).first()
        if not entitlement:
            return None
        if entitlement.limit_type == 'BOOLEAN':
            return entitlement.limit_value_boolean
        elif entitlement.limit_type == 'NUMERIC':
            return entitlement.limit_value_numeric
        elif entitlement.limit_type == 'JSON':
            return entitlement.limit_value_json
        return None

    @staticmethod
    def has_entitlement(tenant, feature_code):
        """
        Check if entitlement is active and boolean limit is True.
        """
        limit = EntitlementValidationService.get_limit(tenant, feature_code)
        if limit is None:
            return False
        if isinstance(limit, bool):
            return limit
        return True

    @staticmethod
    def validate_limit(tenant, feature_code, current_value):
        """
        Validate if current_value is within the entitlement limit.
        """
        if not tenant:
            return False
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        entitlement = TenantProductEntitlement.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            tenant_product__tenant_subscription__status='ACTIVE',
            tenant_product__expires_at__gt=timezone.now(),
            feature_code=feature_code
        ).first()

        if not entitlement:
            return False

        if entitlement.limit_type == 'BOOLEAN':
            return entitlement.limit_value_boolean
        elif entitlement.limit_type == 'NUMERIC':
            if entitlement.limit_value_numeric is None:
                return True
            return current_value <= entitlement.limit_value_numeric
        return True


class UsageTrackingService:
    @staticmethod
    def increment_usage(tenant, metric_code, amount=1):
        """
        Increment live usage consumption.
        """
        if not tenant:
            return None
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        usage = TenantProductUsage.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            metric_code=metric_code
        ).first()

        if not usage:
            # Try to create usage record if a tenant product exists
            tenant_prod = TenantProduct.objects.filter(
                tenant_id=tenant_id,
                status='ACTIVE'
            ).first()
            if not tenant_prod:
                return None
            usage = TenantProductUsage.objects.create(
                tenant_product=tenant_prod,
                metric_code=metric_code,
                usage_value=0,
                usage_limit=100  # Default fallback limit
            )

        usage.usage_value += amount
        if usage.usage_limit > 0:
            usage.percentage_used = Decimal(round((usage.usage_value / usage.usage_limit) * 100, 2))
        else:
            usage.percentage_used = Decimal('0.00')
        usage.save()
        return usage

    @staticmethod
    def decrement_usage(tenant, metric_code, amount=1):
        """
        Decrement live usage consumption.
        """
        if not tenant:
            return None
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        usage = TenantProductUsage.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            metric_code=metric_code
        ).first()

        if not usage:
            return None

        usage.usage_value = max(0, usage.usage_value - amount)
        if usage.usage_limit > 0:
            usage.percentage_used = Decimal(round((usage.usage_value / usage.usage_limit) * 100, 2))
        else:
            usage.percentage_used = Decimal('0.00')
        usage.save()
        return usage

    @staticmethod
    def recalculate_usage(tenant, metric_code):
        """
        Recalculate usage from actual database models based on metric code.
        """
        if not tenant:
            return None
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        usage = TenantProductUsage.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE',
            metric_code=metric_code
        ).first()

        if not usage:
            return None

        # Query actual counts based on metric_code
        actual_value = 0
        if metric_code == 'ROOMS_USED':
            from apps.inventory.models import InventoryUnit
            actual_value = InventoryUnit.objects.filter(property__tenant_id=tenant_id).count()
        elif metric_code == 'ACTIVE_USERS':
            from apps.accounts.models import AppUser
            actual_value = AppUser.objects.filter(tenant_id=tenant_id, is_active=True).count()
        elif metric_code == 'PROPERTIES_USED':
            from apps.tenants.models import Property
            actual_value = Property.objects.filter(tenant_id=tenant_id).count()
        elif metric_code == 'ACTIVE_RESERVATIONS':
            from apps.reservations.models import Reservation
            actual_value = Reservation.objects.filter(tenant_id=tenant_id, status='CONFIRMED').count()
        else:
            # If not automated, keep current usage_value
            actual_value = usage.usage_value

        usage.usage_value = actual_value
        if usage.usage_limit > 0:
            usage.percentage_used = Decimal(round((usage.usage_value / usage.usage_limit) * 100, 2))
        else:
            usage.percentage_used = Decimal('0.00')
        usage.save()
        return usage

    @staticmethod
    def get_usage_summary(tenant):
        """
        Get all usage metrics summary for the tenant.
        """
        if not tenant:
            return []
        tenant_id = tenant.id if hasattr(tenant, 'id') else tenant
        usages = TenantProductUsage.objects.filter(
            tenant_product__tenant_id=tenant_id,
            tenant_product__status='ACTIVE'
        )
        summary = []
        for u in usages:
            summary.append({
                'metric_code': u.metric_code,
                'usage_value': u.usage_value,
                'usage_limit': u.usage_limit,
                'percentage_used': float(u.percentage_used),
                'last_calculated_at': u.last_calculated_at
            })
        return summary
