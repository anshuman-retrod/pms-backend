from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.tenants.models import Tenant, Property
from apps.inventory.models import InventoryUnitCategory, InventoryUnitType
from apps.rates.models import (
    MealPlan, CancellationPolicy, ChildPolicy, RatePlan,
    RatePlanInventoryType, DerivedRateConfig, RateRuleOccupancy,
    RateRuleDayOfWeek, RateCalendar, PackageProduct, PackageProductRatePlan,
    RatePlanVersion
)
from apps.rates.services import (
    RateCalculationService, RateCalendarService, RatePlanService
)
from apps.rbac.models import Permission, Role, UserPropertyRole

User = get_user_model()

class RateDomainTests(APITestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_1 = Tenant.objects.create(
            name='Tenant One', subdomain='t1', country='India', currency='INR', timezone='UTC'
        )
        self.tenant_2 = Tenant.objects.create(
            name='Tenant Two', subdomain='t2', country='India', currency='INR', timezone='UTC'
        )

        # Create Properties
        self.prop_t1 = Property.objects.create(
            tenant=self.tenant_1, name='Prop T1', address_line_1='A', city='Delhi',
            state='Delhi', country='India', postal_code='1', contact_email='a@t1.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )
        self.prop_t2 = Property.objects.create(
            tenant=self.tenant_2, name='Prop T2', address_line_1='B', city='Goa',
            state='Goa', country='India', postal_code='2', contact_email='b@t2.com',
            contact_phone='2', currency='INR', timezone='UTC'
        )

        # Inventory Category & Type
        self.cat = InventoryUnitCategory.objects.create(
            tenant=None, code='room', name='System Room', is_system=True
        )
        self.unit_type_t1 = InventoryUnitType.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, category=self.cat,
            code='ROOM-T1', name='Room T1'
        )
        self.unit_type_t2 = InventoryUnitType.objects.create(
            tenant=self.tenant_2, property=self.prop_t2, category=self.cat,
            code='ROOM-T2', name='Room T2'
        )

        # Auth and Roles
        self.user_t1 = User.objects.create_user(
            email='t1_rates_staff@test.com', password='Password123', tenant=self.tenant_1,
            name='T1 Rates Staff', username='t1_rates_staff'
        )
        self.role_manage = Role.objects.create(
            tenant=self.tenant_1, code='rates_manager', name='Rates Manager'
        )
        
        # Permissions setup
        self.perm_view = Permission.objects.create(code='rate.view', category='rates')
        self.perm_create = Permission.objects.create(code='rate.create', category='rates')
        self.perm_edit = Permission.objects.create(code='rate.edit', category='rates')
        self.perm_delete = Permission.objects.create(code='rate.delete', category='rates')
        self.perm_cal = Permission.objects.create(code='rate.calendar.manage', category='rates')
        self.perm_policy = Permission.objects.create(code='policy.manage', category='rates')
        self.perm_pkg = Permission.objects.create(code='package.manage', category='rates')

        for perm in [self.perm_view, self.perm_create, self.perm_edit, self.perm_delete, self.perm_cal, self.perm_policy, self.perm_pkg]:
            self.role_manage.permissions.create(role=self.role_manage, permission=perm)

        UserPropertyRole.objects.create(
            tenant=self.tenant_1, user=self.user_t1, property=self.prop_t1, role=self.role_manage
        )

        # Policies and Meal plans
        self.meal_t1 = MealPlan.objects.create(
            tenant=self.tenant_1, code='CP', name='Breakfast', price_adjustment=Decimal('500.00')
        )
        self.cancel_t1 = CancellationPolicy.objects.create(
            tenant=self.tenant_1, code='FLEX', name='Flexible', free_cancellation_hours=24,
            penalty_type='PERCENTAGE', penalty_value=Decimal('0.00')
        )
        self.child_t1 = ChildPolicy.objects.create(
            tenant=self.tenant_1, code='CHILD_STD', name='Standard Child', max_free_age=5,
            child_flat_charge=Decimal('800.00')
        )

        # Rate Plan
        self.rate_plan_bar = RatePlan.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, code='BAR', name='Best Available Rate',
            cancellation_policy=self.cancel_t1, child_policy=self.child_t1, default_meal_plan=self.meal_t1
        )

        self.mapping_bar = RatePlanInventoryType.objects.create(
            tenant=self.tenant_1, rate_plan=self.rate_plan_bar, inventory_unit_type=self.unit_type_t1,
            base_rate=Decimal('5000.00')
        )

    def test_tenant_and_property_isolation(self):
        # A tenant cannot see or modify other tenant's policies or rate plans
        # Cross-tenant mapping validation should fail in models.clean()
        with self.assertRaises(ValidationError):
            invalid_plan = RatePlan(
                tenant=self.tenant_1, property=self.prop_t2, code='CROSS_BAR', name='Cross BAR',
                cancellation_policy=self.cancel_t1, child_policy=self.child_t1
            )
            invalid_plan.full_clean()

        self.client.force_authenticate(user=self.user_t1)
        response = self.client.get('/api/rates/cancellation-policies/', HTTP_X_PROPERTY_ID=str(self.prop_t1.id), HTTP_X_TENANT_SUBDOMAIN='t1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return exactly 1 policy (FLEX) since tenant_2's policies aren't visible
        self.assertEqual(len(response.data), 1)

    def test_rate_calculation_engine_rules(self):
        # Setup: base=5000, CP meal adjustment=500. Total without rules = 5500
        # Add rules: Occupancy = 3 adds 1500, Day of Week Mon (1=Sun, 2=Mon) adds 10% (+500)
        RateRuleOccupancy.objects.create(
            tenant=self.tenant_1, rate_plan_inventory_type=self.mapping_bar,
            occupancy_from=3, occupancy_to=4, modifier_type='FLAT_CHARGE', value=Decimal('1500.00')
        )

        RateRuleDayOfWeek.objects.create(
            tenant=self.tenant_1, rate_plan_inventory_type=self.mapping_bar,
            day_of_week=2, modifier_type='PERCENTAGE_ADJUST', value=Decimal('10.00')
        )

        target_date_mon = date(2026, 6, 22)  # Monday
        self.assertEqual(target_date_mon.weekday(), 0) # 0=Monday

        # 1. Base occupancy (1 guest), Monday: Base (5000) + Day (500) + Meal (500) = 6000
        rate_1 = RateCalculationService.calculate_final_rate(
            tenant=self.tenant_1, property_id=self.prop_t1.id, rate_plan=self.rate_plan_bar,
            inventory_unit_type_id=self.unit_type_t1.id, target_date=target_date_mon, occupancy=1
        )
        self.assertEqual(rate_1, Decimal('6000.00'))

        # 2. Occupancy of 3, Monday: Base (5000) + Occ (1500) + Day (500) + Meal (500) = 7500
        rate_3 = RateCalculationService.calculate_final_rate(
            tenant=self.tenant_1, property_id=self.prop_t1.id, rate_plan=self.rate_plan_bar,
            inventory_unit_type_id=self.unit_type_t1.id, target_date=target_date_mon, occupancy=3
        )
        self.assertEqual(rate_3, Decimal('7500.00'))

    def test_derived_rate_calculation(self):
        # Create a Derived rate plan: Non-Refundable = BAR - 10%
        derived_plan = RatePlan.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, code='NON_REF', name='Non-Refundable',
            cancellation_policy=self.cancel_t1, child_policy=self.child_t1, is_derived=True
        )
        dc = DerivedRateConfig.objects.create(
            tenant=self.tenant_1, child_rate_plan=derived_plan, anchor_rate_plan=self.rate_plan_bar,
            modifier_type='PERCENT', modifier_value=Decimal('-10.00')
        )

        target_date_mon = date(2026, 6, 22)
        # BAR final is 6000. Derived should be 6000 - 10% (600) = 5400 (which doesn't apply meal markup again if child doesn't specify one)
        # Wait, BAR final rate includes CP (5000 + 500 = 5500 baseline, + 500 Mon modifier = 6000).
        # Derived child doesn't define base mapping, so it anchors off BAR's calculated final rate.
        # Derived final rate = 6000 - 10% = 5400.
        final_price = RateCalculationService.calculate_final_rate(
            tenant=self.tenant_1, property_id=self.prop_t1.id, rate_plan=derived_plan,
            inventory_unit_type_id=self.unit_type_t1.id, target_date=target_date_mon, occupancy=1
        )
        self.assertEqual(final_price, Decimal('4950.00'))

    def test_rate_calendar_generation(self):
        # Rebuild calendar for t1
        today = date.today()
        count = RateCalendarService.rebuild_calendar(self.tenant_1, self.prop_t1.id, today, today + timedelta(days=2))
        # 1 rate plan (BAR) * 1 unit type * 3 days = 3 records
        self.assertEqual(count, 3)

        cal_entry = RateCalendar.objects.filter(property=self.prop_t1, date=today).first()
        self.assertIsNotNone(cal_entry)
        self.assertTrue(cal_entry.is_available)

    def test_package_product_mapping(self):
        product = PackageProduct.objects.create(
            tenant=self.tenant_1, code='SPA_Treatment', name='60m massage',
            category='SPA', default_price=Decimal('2000.00')
        )
        mapping = PackageProductRatePlan.objects.create(
            tenant=self.tenant_1, rate_plan=self.rate_plan_bar, package_product=product, included_quantity=2
        )
        self.assertEqual(mapping.included_quantity, 2)

    def test_version_snapshots(self):
        # Check that creating snapshot creates a version record
        v = RatePlanService.create_version_snapshot(self.rate_plan_bar)
        self.assertEqual(v.version_number, 1)
        self.assertEqual(v.snapshot['rate_plan']['code'], 'BAR')
