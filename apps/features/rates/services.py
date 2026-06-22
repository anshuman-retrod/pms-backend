from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from datetime import date, timedelta
import logging

from apps.features.rates.models import (
    MealPlan, CancellationPolicy, ChildPolicy, RatePlan,
    RatePlanInventoryType, RatePlanVersion, DerivedRateConfig,
    RateRuleOccupancy, RateRuleDayOfWeek, RateCalendar,
    PackageProduct, PackageProductRatePlan
)
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnitType

logger = logging.getLogger(__name__)

class MealPlanService:
    @staticmethod
    def get_meal_plans(tenant):
        return MealPlan.objects.filter(Q(tenant=tenant) | Q(tenant__isnull=True))


class CancellationPolicyService:
    @staticmethod
    def get_policies(tenant):
        return CancellationPolicy.objects.filter(tenant=tenant)


class ChildPolicyService:
    @staticmethod
    def get_policies(tenant):
        return ChildPolicy.objects.filter(tenant=tenant)


class PackageProductService:
    @staticmethod
    def get_products(tenant):
        return PackageProduct.objects.filter(tenant=tenant)


class DerivedRateService:
    @staticmethod
    def get_derived_rates(tenant):
        return DerivedRateConfig.objects.filter(tenant=tenant)


class RatePlanService:
    @staticmethod
    def create_version_snapshot(rate_plan):
        """
        Takes a snapshot of the current state of a rate plan and saves it as a new version.
        """
        # Gather info for snapshot
        inv_types = RatePlanInventoryType.objects.filter(rate_plan=rate_plan)
        inv_types_data = []
        for it in inv_types:
            occ_rules = RateRuleOccupancy.objects.filter(rate_plan_inventory_type=it)
            day_rules = RateRuleDayOfWeek.objects.filter(rate_plan_inventory_type=it)
            inv_types_data.append({
                'inventory_unit_type_id': str(it.inventory_unit_type_id),
                'base_rate': str(it.base_rate),
                'occupancy_rules': [
                    {
                        'from': r.occupancy_from,
                        'to': r.occupancy_to,
                        'modifier_type': r.modifier_type,
                        'value': str(r.value)
                    } for r in occ_rules
                ],
                'day_of_week_rules': [
                    {
                        'day': r.day_of_week,
                        'modifier_type': r.modifier_type,
                        'value': str(r.value)
                    } for r in day_rules
                ]
            })

        packages = PackageProductRatePlan.objects.filter(rate_plan=rate_plan)
        packages_data = [
            {
                'package_product_id': str(pkg.package_product_id),
                'code': pkg.package_product.code,
                'included_quantity': pkg.included_quantity
            } for pkg in packages
        ]

        derived_data = None
        if rate_plan.is_derived and hasattr(rate_plan, 'derived_config'):
            dc = rate_plan.derived_config
            derived_data = {
                'anchor_rate_plan_id': str(dc.anchor_rate_plan_id),
                'modifier_type': dc.modifier_type,
                'modifier_value': str(dc.modifier_value)
            }

        snapshot = {
            'rate_plan': {
                'id': str(rate_plan.id),
                'code': rate_plan.code,
                'name': rate_plan.name,
                'category': rate_plan.category,
                'is_active': rate_plan.is_active,
                'cancellation_policy': {
                    'id': str(rate_plan.cancellation_policy_id),
                    'code': rate_plan.cancellation_policy.code,
                    'penalty_type': rate_plan.cancellation_policy.penalty_type,
                    'penalty_value': str(rate_plan.cancellation_policy.penalty_value)
                },
                'child_policy': {
                    'id': str(rate_plan.child_policy_id),
                    'code': rate_plan.child_policy.code,
                    'child_flat_charge': str(rate_plan.child_policy.child_flat_charge)
                },
                'default_meal_plan': {
                    'id': str(rate_plan.default_meal_plan_id) if rate_plan.default_meal_plan_id else None,
                    'code': rate_plan.default_meal_plan.code if rate_plan.default_meal_plan else None,
                    'price_adjustment': str(rate_plan.default_meal_plan.price_adjustment) if rate_plan.default_meal_plan else "0.00"
                }
            },
            'inventory_types': inv_types_data,
            'packages': packages_data,
            'derived_config': derived_data
        }

        # Calculate next version number
        latest_version = RatePlanVersion.objects.filter(rate_plan=rate_plan).order_by('-version_number').first()
        next_ver = (latest_version.version_number + 1) if latest_version else 1

        # Expire older active version if any
        now = timezone.now()
        if latest_version:
            latest_version.effective_to = now
            latest_version.save(update_fields=['effective_to'])

        return RatePlanVersion.objects.create(
            rate_plan=rate_plan,
            version_number=next_ver,
            snapshot=snapshot,
            effective_from=now,
            effective_to=None
        )


class RateCalculationService:
    @classmethod
    def calculate_final_rate(cls, tenant, property_id, rate_plan, inventory_unit_type_id, target_date, occupancy=1, meal_plan_override=None, recursion_depth=0):
        """
        Executes Rate Calculation Flow:
        Base Rate
        + Occupancy Rules
        + Day Of Week Rules
        + Derived Rate Adjustments
        + Meal Plan Adjustments
        = Final Rate
        """
        if recursion_depth > 5:
            logger.error("Max recursion depth exceeded for derived rate calculations.")
            raise ValidationError("Circular anchoring detected in derived rates.")

        # 1. Base Rate
        mapping = RatePlanInventoryType.objects.filter(
            rate_plan=rate_plan,
            inventory_unit_type_id=inventory_unit_type_id
        ).first()

        if not mapping:
            if rate_plan.is_derived and hasattr(rate_plan, 'derived_config'):
                # Derived rate might not define base rates directly, instead it anchors to parent.
                # So we fallback to anchor rate plan's mapping or set base_rate to 0 to compute modifiers.
                base_rate = Decimal('0.00')
            else:
                return Decimal('0.00')
        else:
            base_rate = mapping.base_rate

        final_rate = base_rate

        # 2. Occupancy Rules
        if mapping:
            occ_rule = RateRuleOccupancy.objects.filter(
                rate_plan_inventory_type=mapping,
                occupancy_from__lte=occupancy,
                occupancy_to__gte=occupancy
            ).first()
            if occ_rule:
                if occ_rule.modifier_type == 'FLAT_CHARGE':
                    final_rate += occ_rule.value
                elif occ_rule.modifier_type == 'PERCENTAGE_ADJUST':
                    final_rate += base_rate * (occ_rule.value / Decimal('100.0'))

        # 3. Day of Week Rules
        # Day of week in python is 0=Monday to 6=Sunday. Or we use standard index from models (1=Sunday, 7=Saturday).
        # We can map Python weekday to our index:
        # Python: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        # Model: 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri, 7=Sat
        py_day = target_date.weekday()
        days_map = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 1}
        model_day = days_map[py_day]

        if mapping:
            day_rule = RateRuleDayOfWeek.objects.filter(
                rate_plan_inventory_type=mapping,
                day_of_week=model_day
            ).first()
            if day_rule:
                if day_rule.modifier_type == 'FLAT_ADJUST':
                    final_rate += day_rule.value
                elif day_rule.modifier_type == 'PERCENTAGE_ADJUST':
                    final_rate += base_rate * (day_rule.value / Decimal('100.0'))

        # 4. Derived Rate Adjustments
        if rate_plan.is_derived and hasattr(rate_plan, 'derived_config'):
            dc = rate_plan.derived_config
            anchor_rate = cls.calculate_final_rate(
                tenant=tenant,
                property_id=property_id,
                rate_plan=dc.anchor_rate_plan,
                inventory_unit_type_id=inventory_unit_type_id,
                target_date=target_date,
                occupancy=occupancy,
                meal_plan_override=None,
                recursion_depth=recursion_depth + 1
            )
            # If child plan doesn't have custom rules, we adjust anchor rate directly
            if dc.modifier_type == 'PERCENT':
                derived_adjustment = anchor_rate * (dc.modifier_value / Decimal('100.0'))
            else:
                derived_adjustment = dc.modifier_value
            
            # Since flow is Base Rate + Rules + Derived + Meal, if the rate plan has its own base rate mapping,
            # we modify it, otherwise we replace/build off the anchor rate.
            if mapping:
                # Add derived adjustment to current accumulated total
                final_rate = final_rate + derived_adjustment
            else:
                final_rate = anchor_rate + derived_adjustment

        # 5. Meal Plan Adjustments
        meal_plan = meal_plan_override or rate_plan.default_meal_plan
        if meal_plan:
            final_rate += meal_plan.price_adjustment

        return max(Decimal('0.00'), final_rate)


class RateCalendarService:
    @staticmethod
    def rebuild_calendar(tenant, property_id, start_date, end_date):
        """
        Regenerates daily pricing matrix (RateCalendar).
        """
        from apps.features.availability.services import RestrictionService
        
        rate_plans = RatePlan.objects.filter(property_id=property_id, is_active=True)
        unit_types = InventoryUnitType.objects.filter(property_id=property_id)
        
        rebuilt_records = 0
        curr_date = start_date
        
        with transaction.atomic():
            # Delete existing records in range to start fresh
            RateCalendar.objects.filter(
                property_id=property_id,
                date__range=[start_date, end_date]
            ).delete()
            
            while curr_date <= end_date:
                for rp in rate_plans:
                    for ut in unit_types:
                        # Calculate price for base occupancy (1 guest)
                        price = RateCalculationService.calculate_final_rate(
                            tenant=tenant,
                            property_id=property_id,
                            rate_plan=rp,
                            inventory_unit_type_id=ut.id,
                            target_date=curr_date,
                            occupancy=1
                        )
                        
                        # Stop sell check
                        is_available = True
                        try:
                            # Use RestrictionService to check STOP_SELL state
                            is_available = not RestrictionService.is_stop_sell(
                                tenant=tenant,
                                property_id=property_id,
                                date=curr_date,
                                unit_type_id=ut.id,
                                rate_plan_id=rp.id
                            )
                        except Exception as e:
                            logger.debug(f"Error checking stop sell restriction: {e}")
                        
                        RateCalendar.objects.create(
                            property_id=property_id,
                            date=curr_date,
                            rate_plan=rp,
                            inventory_unit_type=ut,
                            amount=price,
                            is_available=is_available
                        )
                        rebuilt_records += 1
                curr_date += timedelta(days=1)
                
        return rebuilt_records
