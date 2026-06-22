from django.core.management.base import BaseCommand
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import (
    InventoryUnitCategory, InventoryUnitType, InventoryUnit,
    InventoryRelationship, AttributeDefinition, InventoryUnitAttribute,
    Amenity, InventoryUnitTypeAmenity, InventoryMedia
)

class Command(BaseCommand):
    help = 'Seed inventory categories, unit types, units, amenities, and attributes for Retrod PMS.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Unified Inventory Domain...")

        # 1. Fetch Tenant and Properties
        tenant_gp = Tenant.objects.filter(subdomain='grandpalace').first()
        if not tenant_gp:
            self.stdout.write(self.style.ERROR("Tenant 'grandpalace' not found. Run seed_pms first!"))
            return

        prop_delhi = Property.objects.filter(tenant=tenant_gp, name__icontains='Delhi').first()
        prop_goa = Property.objects.filter(tenant=tenant_gp, name__icontains='Goa').first()

        if not prop_delhi or not prop_goa:
            self.stdout.write(self.style.ERROR("Properties not found for 'grandpalace'. Run seed_pms first!"))
            return

        # 2. Seed System Categories (tenant=None)
        categories_data = [
            ('room', 'Hotel Room', True),
            ('villa', 'Entire Villa', True),
            ('dorm', 'Hostel Dorm', True),
            ('banquet', 'Banquet & Conference Hall', True),
        ]
        categories = {}
        for code, name, is_system in categories_data:
            cat, created = InventoryUnitCategory.objects.get_or_create(
                tenant=None,
                code=code,
                defaults={'name': name, 'is_system': is_system, 'is_active': True}
            )
            categories[code] = cat
            if created:
                self.stdout.write(f"Created system category: {code}")

        # 3. Seed System Amenities (tenant=None)
        amenities_data = [
            ('wifi', 'High-Speed WiFi', 'connectivity'),
            ('ac', 'Air Conditioning', 'comfort'),
            ('pool', 'Swimming Pool Access', 'facilities'),
            ('projector', 'Projector & Screen', 'business'),
            ('parking', 'Free Parking', 'facilities'),
            ('tv', 'Smart TV', 'entertainment'),
        ]
        amenities = {}
        for code, name, category in amenities_data:
            am, created = Amenity.objects.get_or_create(
                tenant=None,
                code=code,
                defaults={'name': name, 'category': category}
            )
            amenities[code] = am
            if created:
                self.stdout.write(f"Created system amenity: {code}")

        # 4. Seed Attribute Definitions (tenant=None)
        attributes_data = [
            ('bed_type', 'choice', ['king', 'queen', 'twin', 'single']),
            ('smoking_allowed', 'boolean', None),
            ('view_type', 'choice', ['sea', 'garden', 'pool', 'city']),
            ('capacity_adults', 'number', None),
        ]
        attr_defs = {}
        for code, data_type, allowed in attributes_data:
            ad, created = AttributeDefinition.objects.get_or_create(
                tenant=None,
                code=code,
                defaults={'data_type': data_type, 'allowed_values': allowed}
            )
            attr_defs[code] = ad
            if created:
                self.stdout.write(f"Created system attribute definition: {code}")

        # 5. Create Unit Types for Goa Property
        # Deluxe Sea View Villa
        villa_type, _ = InventoryUnitType.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            code='DLX-VILLA',
            defaults={
                'name': 'Deluxe 3-Bedroom Villa',
                'category': categories['villa'],
                'base_occupancy': 6,
                'max_occupancy': 9,
                'max_adults': 9,
                'max_children': 4,
                'max_infants': 2,
                'is_sellable': True
            }
        )

        # Standard Room Goa
        goa_std_type, _ = InventoryUnitType.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            code='GOA-STD',
            defaults={
                'name': 'Standard Garden Room',
                'category': categories['room'],
                'base_occupancy': 2,
                'max_occupancy': 3,
                'max_adults': 3,
                'max_children': 1,
                'max_infants': 1,
                'is_sellable': True
            }
        )

        # 6. Create Unit Types for Delhi Property
        # Executive Suite
        suite_type, _ = InventoryUnitType.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_delhi,
            code='EXEC-SUITE',
            defaults={
                'name': 'Executive Suite Delhi',
                'category': categories['room'],
                'base_occupancy': 2,
                'max_occupancy': 4,
                'max_adults': 4,
                'max_children': 2,
                'max_infants': 1,
                'is_sellable': True
            }
        )

        # Grand Ballroom
        ballroom_type, _ = InventoryUnitType.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_delhi,
            code='BALLROOM',
            defaults={
                'name': 'Grand Ballroom',
                'category': categories['banquet'],
                'base_occupancy': 100,
                'max_occupancy': 250,
                'max_adults': 250,
                'max_children': 50,
                'max_infants': 10,
                'is_sellable': True
            }
        )

        # Link Amenities to Goa Deluxe Villa
        for am_code in ['wifi', 'ac', 'pool', 'parking']:
            InventoryUnitTypeAmenity.objects.get_or_create(
                tenant=tenant_gp,
                inventory_unit_type=villa_type,
                amenity=amenities[am_code]
            )

        # Link Amenities to Delhi Ballroom
        for am_code in ['ac', 'projector', 'wifi']:
            InventoryUnitTypeAmenity.objects.get_or_create(
                tenant=tenant_gp,
                inventory_unit_type=ballroom_type,
                amenity=amenities[am_code]
            )

        # Map Attributes to Goa Deluxe Villa type
        InventoryUnitAttribute.objects.get_or_create(
            tenant=tenant_gp,
            inventory_unit_type=villa_type,
            attribute_definition=attr_defs['bed_type'],
            defaults={'value': 'king'}
        )
        InventoryUnitAttribute.objects.get_or_create(
            tenant=tenant_gp,
            inventory_unit_type=villa_type,
            attribute_definition=attr_defs['view_type'],
            defaults={'value': 'sea'}
        )
        InventoryUnitAttribute.objects.get_or_create(
            tenant=tenant_gp,
            inventory_unit_type=villa_type,
            attribute_definition=attr_defs['smoking_allowed'],
            defaults={'value': 'false'}
        )

        # 7. Seed Physical Inventory Units
        # Goa units
        villa_1, _ = InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            name='Ocean Villa 1',
            defaults={
                'inventory_unit_type': villa_type,
                'floor': 'Ground',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )
        villa_2, _ = InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            name='Ocean Villa 2',
            defaults={
                'inventory_unit_type': villa_type,
                'floor': 'Ground',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )
        
        # Sub-units of Ocean Villa 1 (Bedroom A & B)
        v1_bed_a, _ = InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            name='Ocean Villa 1 - Bedroom A',
            defaults={
                'inventory_unit_type': goa_std_type,
                'parent_unit': villa_1,
                'floor': 'Ground',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )
        v1_bed_b, _ = InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_goa,
            name='Ocean Villa 1 - Bedroom B',
            defaults={
                'inventory_unit_type': goa_std_type,
                'parent_unit': villa_1,
                'floor': 'Ground',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )

        # Set compositions in Relationship Table
        InventoryRelationship.objects.get_or_create(
            tenant=tenant_gp,
            parent_unit=villa_1,
            child_unit=v1_bed_a,
            defaults={'relation_type': 'composition'}
        )
        InventoryRelationship.objects.get_or_create(
            tenant=tenant_gp,
            parent_unit=villa_1,
            child_unit=v1_bed_b,
            defaults={'relation_type': 'composition'}
        )

        # Delhi Units
        InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_delhi,
            name='Executive Suite 301',
            defaults={
                'inventory_unit_type': suite_type,
                'floor': '3rd Floor',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )
        InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_delhi,
            name='Executive Suite 302',
            defaults={
                'inventory_unit_type': suite_type,
                'floor': '3rd Floor',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )
        InventoryUnit.objects.get_or_create(
            tenant=tenant_gp,
            property=prop_delhi,
            name='Main Ballroom A',
            defaults={
                'inventory_unit_type': ballroom_type,
                'floor': 'Mezzanine',
                'operational_status': 'operational',
                'housekeeping_status': 'clean',
                'maintenance_status': 'none'
            }
        )

        # Seed some media URL records
        InventoryMedia.objects.get_or_create(
            tenant=tenant_gp,
            inventory_unit_type=villa_type,
            media_url='https://images.retrod.io/grandpalace/deluxe-villa.jpg',
            defaults={'media_type': 'image', 'sort_order': 1}
        )
        InventoryMedia.objects.get_or_create(
            tenant=tenant_gp,
            inventory_unit_type=villa_type,
            media_url='https://images.retrod.io/grandpalace/deluxe-villa-floorplan.pdf',
            defaults={'media_type': 'floorplan', 'sort_order': 2}
        )

        self.stdout.write(self.style.SUCCESS("Inventory database successfully seeded!"))
