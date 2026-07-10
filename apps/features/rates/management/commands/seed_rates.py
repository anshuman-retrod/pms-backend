from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnitType
from apps.features.rates.models import (
    MealPlan, CancellationPolicy, ChildPolicy, RatePlan,
    RatePlanInventoryType, DerivedRateConfig, RateRuleOccupancy,
    RateRuleDayOfWeek, HospitalityPackage
)
from apps.features.rates.services import RateCalendarService, RatePlanService

class Command(BaseCommand):
    help = 'Seed Meal Plans, Policies, Rate Plans, derived configurations, rules, package products and generate Rate Calendar.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Rate Management Domain...")

        # 1. Fetch Tenant and Properties
        tenant_gp = Tenant.objects.filter(subdomain='grandpalace').first()
        if not tenant_gp:
            self.stdout.write(self.style.ERROR("Tenant 'grandpalace' not found. Run seed_pms first!"))
            return

        properties = Property.objects.filter(tenant=tenant_gp)
        if not properties.exists():
            self.stdout.write(self.style.ERROR("Properties not found for 'grandpalace'. Run seed_pms first!"))
            return

        # 2. Seed Meal Plans (EP, CP, MAP, AP)
        meal_plans = {}
        meal_data = [
            ('EP', 'European Plan (Room Only)', '0.00'),
            ('CP', 'Continental Plan (Bed & Breakfast)', '500.00'),
            ('MAP', 'Modified American Plan (Half Board)', '1200.00'),
            ('AP', 'American Plan (Full Board)', '2000.00'),
        ]
        for code, name, adj in meal_data:
            mp, created = MealPlan.objects.get_or_create(
                tenant=tenant_gp,
                code=code,
                defaults={'name': name, 'price_adjustment': Decimal(adj), 'tax_percent': Decimal('5.0')}
            )
            meal_plans[code] = mp
            if created:
                self.stdout.write(f"Created meal plan: {code}")

        # 3. Seed Cancellation Policies
        cancel_policies = {}
        cancel_data = [
            ('FLEX_24H', 'Flexible 24 Hours', 24, 'PERCENTAGE', '0.00'),
            ('NON_REF', 'Non Refundable', 0, 'PERCENTAGE', '100.00'),
        ]
        for code, name, hours, p_type, p_val in cancel_data:
            cp, created = CancellationPolicy.objects.get_or_create(
                tenant=tenant_gp,
                code=code,
                defaults={
                    'name': name,
                    'free_cancellation_hours': hours,
                    'penalty_type': p_type,
                    'penalty_value': Decimal(p_val)
                }
            )
            cancel_policies[code] = cp
            if created:
                self.stdout.write(f"Created cancellation policy: {code}")

        # 4. Seed Child Policies
        child_policies = {}
        child_data = [
            ('CHILD_STD', 'Standard Child Policy', 5, 6, 12, '800.00'),
        ]
        for code, name, free_age, charge_from, charge_to, charge in child_data:
            cp, created = ChildPolicy.objects.get_or_create(
                tenant=tenant_gp,
                code=code,
                defaults={
                    'name': name,
                    'max_free_age': free_age,
                    'charge_age_from': charge_from,
                    'charge_age_to': charge_to,
                    'child_flat_charge': Decimal(charge)
                }
            )
            child_policies[code] = cp
            if created:
                self.stdout.write(f"Created child policy: {code}")

        # 5. Seed Hospitality Packages
        packages = {}
        pkg_data = [
            ('Honeymoon Escape', '85000.00', 'Suite, Dinner, Spa, Airport Transfer'),
            ('Wellness Retreat', '42000.00', 'Deluxe, Yoga Session, Organic Breakfast'),
            ('Family Fun', '38000.00', 'Twin Room, Kids Club Access, Lunch Included'),
        ]
        for name, price, inclusions in pkg_data:
            hp, created = HospitalityPackage.objects.get_or_create(
                tenant=tenant_gp,
                name=name,
                defaults={'price': Decimal(price), 'inclusions': inclusions, 'status': 'Active'}
            )
            packages[name] = hp
            if created:
                self.stdout.write(f"Created hospitality package: {name}")

        # 6. Seed Rate Plans per Property
        for prop in properties:
            # DLX-BAR (Best Available Rate)
            bar_plan, created = RatePlan.objects.get_or_create(
                tenant=tenant_gp,
                property=prop,
                code='BAR',
                defaults={
                    'name': f'Best Available Rate - {prop.name}',
                    'cancellation_policy': cancel_policies['FLEX_24H'],
                    'child_policy': child_policies['CHILD_STD'],
                    'default_meal_plan': meal_plans['CP'],
                    'category': 'bar',
                    'is_derived': False
                }
            )
            if created:
                self.stdout.write(f"Created BAR plan for {prop.name}")
                RatePlanService.create_version_snapshot(bar_plan)

            # NON_REF (Derived Rate Plan: BAR - 10%)
            nonref_plan, created = RatePlan.objects.get_or_create(
                tenant=tenant_gp,
                property=prop,
                code='NON_REF',
                defaults={
                    'name': f'Non-Refundable Promo - {prop.name}',
                    'cancellation_policy': cancel_policies['NON_REF'],
                    'child_policy': child_policies['CHILD_STD'],
                    'default_meal_plan': meal_plans['CP'],
                    'category': 'promotional',
                    'is_derived': True
                }
            )
            if created:
                self.stdout.write(f"Created Non-Refundable derived plan for {prop.name}")
                # Create derived modifier mapping
                DerivedRateConfig.objects.get_or_create(
                    tenant=tenant_gp,
                    child_rate_plan=nonref_plan,
                    defaults={
                        'anchor_rate_plan': bar_plan,
                        'modifier_type': 'PERCENT',
                        'modifier_value': Decimal('-10.00') # 10% discount
                    }
                )
                RatePlanService.create_version_snapshot(nonref_plan)

            # Seed base rates and rules for unit types
            unit_types = InventoryUnitType.objects.filter(property=prop)
            for ut in unit_types:
                # Nightly Baseline
                base_rate = Decimal('3500.00')
                if ut.code == 'DLX-VILLA':
                    base_rate = Decimal('12000.00')
                elif ut.code == 'EXEC-SUITE':
                    base_rate = Decimal('7500.00')
                elif ut.code == 'BALLROOM':
                    base_rate = Decimal('25000.00')

                # Base Rate mapping for BAR
                mapping, m_created = RatePlanInventoryType.objects.get_or_create(
                    tenant=tenant_gp,
                    rate_plan=bar_plan,
                    inventory_unit_type=ut,
                    defaults={'base_rate': base_rate}
                )

                if m_created:
                    # Seed Occupancy Rule for 3+ guests (adds 1500)
                    RateRuleOccupancy.objects.create(
                        tenant=tenant_gp,
                        rate_plan_inventory_type=mapping,
                        occupancy_from=3,
                        occupancy_to=99,
                        modifier_type='FLAT_CHARGE',
                        value=Decimal('1500.00')
                    )

                    # Weekend Surcharge for Saturday/Sunday (+10%)
                    for d_index in [1, 7]: # Sunday, Saturday
                        RateRuleDayOfWeek.objects.create(
                            tenant=tenant_gp,
                            rate_plan_inventory_type=mapping,
                            day_of_week=d_index,
                            modifier_type='PERCENTAGE_ADJUST',
                            value=Decimal('10.00')
                        )
            
            # Removed PackageProductRatePlan mapping as it is no longer needed

            # Rebuild rate calendar for next 30 days
            today = date.today()
            end_date = today + timedelta(days=30)
            rebuilt_count = RateCalendarService.rebuild_calendar(tenant_gp, prop.id, today, end_date)
            self.stdout.write(f"Rebuilt {rebuilt_count} rate calendar entries for {prop.name}.")

        self.stdout.write(self.style.SUCCESS("Rates database successfully seeded!"))
