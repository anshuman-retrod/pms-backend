from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from apps.tenants.models import Tenant, Property
from apps.inventory.models import InventoryUnitType, InventoryUnit
from apps.availability.models import InventoryAvailability, InventoryRestriction, InventoryHold

class Command(BaseCommand):
    help = 'Seed demo availability matrix, restrictions, and temporary holds for Retrod PMS.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Availability Domain...")

        # 1. Fetch Tenant and Properties
        tenant_gp = Tenant.objects.filter(subdomain='grandpalace').first()
        if not tenant_gp:
            self.stdout.write(self.style.ERROR("Tenant 'grandpalace' not found. Run seed_pms and seed_inventory first!"))
            return

        properties = Property.objects.filter(tenant=tenant_gp)
        if not properties.exists():
            self.stdout.write(self.style.ERROR("Properties not found for 'grandpalace'. Run seed_pms first!"))
            return

        # 2. Seed availability daily matrix for next 30 days
        today = date.today()
        seeded_availability_count = 0
        
        for prop in properties:
            unit_types = InventoryUnitType.objects.filter(property=prop)
            for ut in unit_types:
                # Get units quantity to determine allocated count
                units_count = InventoryUnit.objects.filter(inventory_unit_type=ut).count()
                # Default to 5 if no units seeded
                allocated = units_count if units_count > 0 else 5
                
                for i in range(30):
                    curr_date = today + timedelta(days=i)
                    
                    # Some simple mock occupancy variation
                    sold = 0
                    if i % 3 == 0:
                        sold = min(allocated, 1)
                    elif i % 5 == 0:
                        sold = min(allocated, 2)
                        
                    blocked = 1 if i % 7 == 0 else 0
                    overbooking = 2 if ut.code == 'EXEC-SUITE' else 0
                    
                    avail, created = InventoryAvailability.objects.get_or_create(
                        tenant=tenant_gp,
                        property=prop,
                        date=curr_date,
                        inventory_unit_type=ut,
                        defaults={
                            'allocated_count': allocated,
                            'sold_count': sold,
                            'blocked_count': blocked,
                            'overbooking_limit': overbooking
                        }
                    )
                    if created:
                        seeded_availability_count += 1

        self.stdout.write(f"Seeded {seeded_availability_count} daily availability records.")

        # 3. Seed some restrictions
        # Set CTA on today + 3 for Goan deluxe villa
        dlx_villa = InventoryUnitType.objects.filter(property__tenant=tenant_gp, code='DLX-VILLA').first()
        if dlx_villa:
            # CTA
            InventoryRestriction.objects.get_or_create(
                tenant=tenant_gp,
                property=dlx_villa.property,
                date=today + timedelta(days=3),
                inventory_unit_type=dlx_villa,
                restriction_type='CTA',
                defaults={'restriction_value': None}
            )
            # Min LOS of 3 nights starting from today + 5
            InventoryRestriction.objects.get_or_create(
                tenant=tenant_gp,
                property=dlx_villa.property,
                date=today + timedelta(days=5),
                inventory_unit_type=dlx_villa,
                restriction_type='MIN_LOS',
                defaults={'restriction_value': 3}
            )
            # Stop Sell on today + 10
            InventoryRestriction.objects.get_or_create(
                tenant=tenant_gp,
                property=dlx_villa.property,
                date=today + timedelta(days=10),
                inventory_unit_type=dlx_villa,
                restriction_type='STOP_SELL',
                defaults={'restriction_value': None}
            )
            self.stdout.write("Seeded restrictions (CTA, MIN_LOS, STOP_SELL) for DLX-VILLA.")

        # 4. Seed some active holds
        # Create an active shopping cart hold expiring in 15 mins for Deluxe Villa
        if dlx_villa:
            InventoryHold.objects.create(
                tenant=tenant_gp,
                property=dlx_villa.property,
                inventory_unit_type=dlx_villa,
                hold_type='CART',
                quantity=1,
                expires_at=timezone.now() + timedelta(minutes=15),
                status='ACTIVE'
            )
            # Create a promotional block hold for 2 villas expiring in 5 days
            InventoryHold.objects.create(
                tenant=tenant_gp,
                property=dlx_villa.property,
                inventory_unit_type=dlx_villa,
                hold_type='PROMOTIONAL',
                quantity=2,
                expires_at=timezone.now() + timedelta(days=5),
                status='ACTIVE'
            )
            self.stdout.write("Seeded active holds (CART, PROMOTIONAL) for DLX-VILLA.")

        self.stdout.write(self.style.SUCCESS("Availability database successfully seeded!"))
