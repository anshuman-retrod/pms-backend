from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.test import APITestCase
from apps.core.tenants.models import Tenant, Property
from apps.core.accounts.models import AppUser
from apps.features.inventory.models import (
    InventoryUnitCategory, InventoryUnitType, InventoryUnit,
    InventoryRelationship, AttributeDefinition, InventoryUnitAttribute,
    Amenity, InventoryUnitTypeAmenity, InventoryMedia,
    Building, Floor, FloorPlan
)
from apps.features.inventory.services import (
    InventoryUnitService, InventoryRelationshipService,
    InventoryAttributeService, AmenityService, InventoryMediaService
)

class InventoryTestCase(TestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_1 = Tenant.objects.create(
            name='Tenant One', subdomain='t1', country='India', currency='INR', timezone='UTC'
        )
        self.tenant_2 = Tenant.objects.create(
            name='Tenant Two', subdomain='t2', country='India', currency='INR', timezone='UTC'
        )

        # Create Properties
        self.prop_t1_a = Property.objects.create(
            tenant=self.tenant_1, name='Prop T1 A', address_line_1='A', city='Delhi',
            state='Delhi', country='India', postal_code='1', contact_email='a@t1.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )
        self.prop_t1_b = Property.objects.create(
            tenant=self.tenant_1, name='Prop T1 B', address_line_1='B', city='Delhi',
            state='Delhi', country='India', postal_code='1', contact_email='b@t1.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )
        self.prop_t2 = Property.objects.create(
            tenant=self.tenant_2, name='Prop T2', address_line_1='C', city='Goa',
            state='Goa', country='India', postal_code='2', contact_email='c@t2.com',
            contact_phone='2', currency='INR', timezone='UTC'
        )

        # Categories
        self.system_cat = InventoryUnitCategory.objects.create(
            tenant=None, code='room', name='System Room', is_system=True
        )
        self.tenant_cat = InventoryUnitCategory.objects.create(
            tenant=self.tenant_1, code='custom', name='Custom Category'
        )

        # Goa/Delhi Unit Types
        self.unit_type_a = InventoryUnitType.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, category=self.system_cat,
            code='TYPE-A', name='Type A Room'
        )
        self.unit_type_b = InventoryUnitType.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_b, category=self.system_cat,
            code='TYPE-B', name='Type B Room'
        )

    def test_tenant_isolation_category_uniqueness(self):
        # System category allows same code globally, but tenant-level custom must be unique per tenant
        with self.assertRaises(Exception):
            with transaction.atomic():
                InventoryUnitCategory.objects.create(
                    tenant=self.tenant_1, code='custom', name='Duplicate'
                )
        
        # Other tenant can create same custom category code
        t2_cat = InventoryUnitCategory.objects.create(
            tenant=self.tenant_2, code='custom', name='T2 Custom Category'
        )
        self.assertIsNotNone(t2_cat)

    def test_property_isolation_unit_type(self):
        # Cannot create unit type mapping with property from different tenant
        with self.assertRaises(ValidationError):
            InventoryUnitService.create_unit(
                tenant=self.tenant_2,
                property=self.prop_t1_a,
                inventory_unit_type=self.unit_type_a,
                name='Invalid Room'
            )

    def test_circular_parent_validation(self):
        # Create normal unit
        unit_1 = InventoryUnit.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, inventory_unit_type=self.unit_type_a,
            name='Unit 1'
        )
        unit_2 = InventoryUnit.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, inventory_unit_type=self.unit_type_a,
            name='Unit 2', parent_unit=unit_1
        )
        
        # Setting unit 1's parent to unit 2 must fail (Circular reference)
        with self.assertRaises(ValidationError):
            InventoryUnitService.update_unit(unit_1, parent_unit=unit_2)

    def test_self_and_circular_relationship_validation(self):
        unit_1 = InventoryUnit.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, inventory_unit_type=self.unit_type_a,
            name='Unit 1'
        )
        unit_2 = InventoryUnit.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, inventory_unit_type=self.unit_type_a,
            name='Unit 2'
        )

        # Self-relationship is not allowed
        with self.assertRaises(ValidationError):
            InventoryRelationshipService.create_relationship(self.tenant_1, unit_1, unit_1)

        # Add unit 1 -> unit 2
        rel1 = InventoryRelationshipService.create_relationship(self.tenant_1, unit_1, unit_2)
        self.assertIsNotNone(rel1)

        # Adding unit 2 -> unit 1 must fail (Circular composition)
        with self.assertRaises(ValidationError):
            InventoryRelationshipService.create_relationship(self.tenant_1, unit_2, unit_1)

    def test_amenity_mapping(self):
        amenity = Amenity.objects.create(tenant=None, code='wifi', name='WiFi', category='connectivity')
        
        mapping, created = AmenityService.map_amenity_to_type(self.tenant_1, self.unit_type_a, amenity)
        self.assertTrue(created)
        self.assertEqual(mapping.inventory_unit_type, self.unit_type_a)

        # Mapping property from another tenant must fail
        with self.assertRaises(ValidationError):
            AmenityService.map_amenity_to_type(self.tenant_2, self.unit_type_a, amenity)

    def test_attribute_assignment_validations(self):
        boolean_def = AttributeDefinition.objects.create(
            tenant=None, code='is_suite', data_type='boolean'
        )
        choice_def = AttributeDefinition.objects.create(
            tenant=None, code='bed_type', data_type='choice', allowed_values=['king', 'queen']
        )

        # Assign correct boolean
        attr_bool = InventoryAttributeService.create_unit_attribute(
            tenant=self.tenant_1, attribute_definition=boolean_def, value='true',
            inventory_unit_type=self.unit_type_a
        )
        self.assertEqual(attr_bool.value, 'true')

        # Invalid boolean
        with self.assertRaises(ValidationError):
            InventoryAttributeService.create_unit_attribute(
                tenant=self.tenant_1, attribute_definition=boolean_def, value='maybe',
                inventory_unit_type=self.unit_type_a
            )

        # Invalid choice value
        with self.assertRaises(ValidationError):
            InventoryAttributeService.create_unit_attribute(
                tenant=self.tenant_1, attribute_definition=choice_def, value='single',
                inventory_unit_type=self.unit_type_a
            )

    def test_media_upload_metadata(self):
        unit_1 = InventoryUnit.objects.create(
            tenant=self.tenant_1, property=self.prop_t1_a, inventory_unit_type=self.unit_type_a,
            name='Unit 1'
        )

        media = InventoryMediaService.create_media(
            tenant=self.tenant_1, media_url='https://images.io/floor.png',
            media_type='floorplan', sort_order=1, inventory_unit=unit_1
        )
        self.assertEqual(media.media_type, 'floorplan')
        self.assertEqual(media.inventory_unit, unit_1)

        # Target both unit and unit type must fail
        with self.assertRaises(ValidationError):
            InventoryMediaService.create_media(
                tenant=self.tenant_1, media_url='https://images.io/floor.png',
                inventory_unit_type=self.unit_type_a, inventory_unit=unit_1
            )


class BuildingFloorAPITests(APITestCase):
    def setUp(self):
        from apps.core.accounts.models import AppUser
        self.tenant = Tenant.objects.create(
            name='Test Tenant', subdomain='test', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Alpha', address_line_1='Street', city='Delhi',
            state='Delhi', country='India', postal_code='110001', contact_email='alpha@test.com',
            contact_phone='+9111', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@test.com', password='Password123', tenant=self.tenant, name='Admin', username='admin',
            is_superuser=True, is_staff=True
        )
        # Authorize user to property
        from apps.core.rbac.models import Role, UserPropertyRole
        self.role = Role.objects.create(tenant=self.tenant, name='Admin Role', code='admin')
        UserPropertyRole.objects.create(user=self.user, tenant=self.tenant, property=self.property, role=self.role)

        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='test')
        self.client.force_authenticate(user=self.user)

    def test_building_floor_floorplan_crud(self):
        # Create Building
        response = self.client.post('/api/buildings/', {
            'property': str(self.property.id),
            'code': 'B1',
            'name': 'Building One',
            'description': 'Main Block'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        building_id = response.data['id']

        # Create Floor
        response = self.client.post('/api/floors/', {
            'building': building_id,
            'floor_number': 1,
            'name': 'First Floor'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        floor_id = response.data['id']

        # Create Floor Plan
        response = self.client.post('/api/floor-plans/', {
            'floor': floor_id,
            'file_url': 'https://images.io/floor1.png',
            'version': '1.0'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        floor_plan_id = response.data['id']

        # List Buildings
        response = self.client.get('/api/buildings/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        # List Floors
        response = self.client.get('/api/floors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        # List Floor Plans
        response = self.client.get('/api/floor-plans/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class InventoryCloneTests(APITestCase):
    def setUp(self):
        from apps.core.accounts.models import AppUser
        from apps.core.rbac.models import Role, UserPropertyRole, Permission, RolePermission
        from apps.features.rates.models import RatePlan, RatePlanInventoryType, RateRuleOccupancy, CancellationPolicy, ChildPolicy

        self.tenant = Tenant.objects.create(
            name='Clone Tenant', subdomain='clone', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Clone', address_line_1='A', city='Goa',
            state='Goa', country='India', postal_code='1', contact_email='clone@test.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='user@clone.com', password='Password123', tenant=self.tenant, name='User', username='cloneuser'
        )
        
        # Setup RBAC role with inventory_type.clone permission
        self.role = Role.objects.create(tenant=self.tenant, name='Cloner', code='cloner')
        self.perm = Permission.objects.create(code='inventory_type.clone', category='inventory')
        RolePermission.objects.create(role=self.role, permission=self.perm)
        UserPropertyRole.objects.create(user=self.user, tenant=self.tenant, property=self.property, role=self.role)

        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='clone', HTTP_X_PROPERTY_ID=str(self.property.id))
        self.client.force_authenticate(user=self.user)

        self.cat = InventoryUnitCategory.objects.create(
            tenant=self.tenant, code='rm', name='Room Category'
        )

        # Source unit type
        self.source_type = InventoryUnitType.objects.create(
            tenant=self.tenant, property=self.property, category=self.cat,
            code='SRC', name='Source Type', base_occupancy=2, max_occupancy=4,
            max_adults=3, max_children=1, max_infants=1, is_sellable=True
        )

        # Amenity
        self.amenity = Amenity.objects.create(tenant=self.tenant, code='wifi', name='WiFi', category='connectivity')
        InventoryUnitTypeAmenity.objects.create(tenant=self.tenant, inventory_unit_type=self.source_type, amenity=self.amenity)

        # Attribute
        self.attr_def = AttributeDefinition.objects.create(tenant=self.tenant, code='bed', data_type='text')
        InventoryUnitAttribute.objects.create(tenant=self.tenant, inventory_unit_type=self.source_type, attribute_definition=self.attr_def, value='King')

        # Media
        InventoryMedia.objects.create(tenant=self.tenant, inventory_unit_type=self.source_type, media_url='https://hotel.com/img.jpg', media_type='image', sort_order=1)

        # Create policies
        self.cancel_policy = CancellationPolicy.objects.create(tenant=self.tenant, code='standard_cancel', name='Standard Cancellation')
        self.child_policy = ChildPolicy.objects.create(tenant=self.tenant, code='standard_child', name='Standard Child Policy')

        # Rate Plan + Occupancy Rule
        self.rate_plan = RatePlan.objects.create(
            tenant=self.tenant, property=self.property, code='BAR', name='Best Available Rate',
            cancellation_policy=self.cancel_policy, child_policy=self.child_policy
        )
        self.rp_it = RatePlanInventoryType.objects.create(tenant=self.tenant, rate_plan=self.rate_plan, inventory_unit_type=self.source_type, base_rate=100.0)
        RateRuleOccupancy.objects.create(tenant=self.tenant, rate_plan_inventory_type=self.rp_it, occupancy_from=3, occupancy_to=4, modifier_type='FLAT_CHARGE', value=20.0)

    def test_clone_success(self):
        # We explicitly pass clone_media = True
        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'Cloned Premium Room',
            'code': 'CLONED_PREMIUM',
            'clone_media': True
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['code'], 'CLONED_PREMIUM')
        self.assertEqual(response.data['status'], 'ACTIVE')
        self.assertEqual(response.data['amenities_copied'], 1)
        self.assertEqual(response.data['attributes_copied'], 1)
        self.assertEqual(response.data['media_copied'], 1)

        # Verify new type copy exists
        new_type = InventoryUnitType.objects.get(id=response.data['id'])
        self.assertEqual(new_type.base_occupancy, 2)
        self.assertEqual(new_type.max_occupancy, 4)

        # Verify amenities copied
        self.assertTrue(InventoryUnitTypeAmenity.objects.filter(inventory_unit_type=new_type, amenity=self.amenity).exists())

        # Verify attributes copied
        self.assertTrue(InventoryUnitAttribute.objects.filter(inventory_unit_type=new_type, attribute_definition=self.attr_def, value='King').exists())

        # Verify media copied because clone_media was True
        self.assertTrue(InventoryMedia.objects.filter(inventory_unit_type=new_type, media_url='https://hotel.com/img.jpg').exists())

        # Verify rate plans / rate rules NOT copied
        from apps.features.rates.models import RatePlanInventoryType
        self.assertFalse(RatePlanInventoryType.objects.filter(inventory_unit_type=new_type).exists())

        # Verify audit log generated with exact fields
        from apps.core.audit.models import AuditLog
        audit = AuditLog.objects.filter(action_type='INVENTORY_TYPE_CLONED', target_id=str(new_type.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.payload_after['source_inventory_type_id'], str(self.source_type.id))
        self.assertEqual(audit.payload_after['new_inventory_type_id'], str(new_type.id))
        self.assertEqual(audit.payload_after['source_name'], self.source_type.name)
        self.assertEqual(audit.payload_after['new_name'], new_type.name)
        self.assertEqual(audit.payload_after['cloned_by'], str(self.user.id))
        self.assertEqual(audit.payload_after['clone_depth'], 1)
        self.assertIn('timestamp', audit.payload_after)

        # Clone again from the new type to verify clone_depth is 2
        response2 = self.client.post(f'/api/inventory/types/{new_type.id}/clone/', {
            'name': 'Grand Premium Room',
            'code': 'GRAND_PREMIUM',
            'clone_media': False
        }, format='json')
        self.assertEqual(response2.status_code, 201)
        grand_type = InventoryUnitType.objects.get(id=response2.data['id'])
        audit2 = AuditLog.objects.filter(action_type='INVENTORY_TYPE_CLONED', target_id=str(grand_type.id)).first()
        self.assertIsNotNone(audit2)
        self.assertEqual(audit2.payload_after['clone_depth'], 2)

    def test_clone_no_media(self):
        # We explicitly pass clone_media = False
        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'Cloned Premium No Media',
            'code': 'CLONED_NO_MEDIA',
            'clone_media': False
        }, format='json')
        self.assertEqual(response.status_code, 201)
        new_type = InventoryUnitType.objects.get(id=response.data['id'])
        # Verify media was NOT copied
        self.assertFalse(InventoryMedia.objects.filter(inventory_unit_type=new_type).exists())

    def test_transaction_rollback(self):
        # Simulate a database failure during copying by mocking a model save / creation to fail.
        # We can mock InventoryUnitAttribute.objects.create to raise an IntegrityError or similar.
        from unittest.mock import patch
        from django.db import IntegrityError

        initial_count = InventoryUnitType.objects.count()

        with patch('apps.features.inventory.models.InventoryUnitAttribute.objects.create', side_effect=IntegrityError("Simulated DB failure during cloning attributes")):
            response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
                'name': 'Should Rollback Room',
                'code': 'SHOULD_ROLLBACK',
                'clone_media': True
            }, format='json')
            
            self.assertEqual(response.status_code, 400)
            self.assertIn('Cloning failed', response.data['error'])

        # Verify no partial InventoryUnitType was created
        self.assertEqual(InventoryUnitType.objects.count(), initial_count)

    def test_duplicate_code_rejected(self):
        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'Cloned Premium Room',
            'code': 'SRC'  # Same code
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.data['error'])

    def test_duplicate_name_rejected(self):
        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'Source Type',  # Same name
            'code': 'NEW_CODE'
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.data['error'])

    def test_archived_source_rejected(self):
        from django.utils import timezone
        self.source_type.deleted_at = timezone.now()
        self.source_type.save()

        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'New Type',
            'code': 'NEW_CODE'
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('inactive', response.data['error'])

    def test_tenant_isolation(self):
        other_tenant = Tenant.objects.create(name='Other Tenant', subdomain='other', country='India', currency='INR', timezone='UTC')
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='other')
        
        # Should be forbidden/not found because of tenant change
        response = self.client.post(f'/api/inventory/types/{self.source_type.id}/clone/', {
            'name': 'New Type',
            'code': 'NEW_CODE'
        }, format='json')
        self.assertEqual(response.status_code, 403)


class InventoryAnalyticsTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Analytics Tenant', subdomain='analytics', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Analytics', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='analytics@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@analytics.com', password='Password123', tenant=self.tenant, name='Admin', username='analyticsadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='analytics')
        self.client.force_authenticate(user=self.user)

    def test_analytics_endpoints(self):
        # 1. Summary
        res = self.client.get('/api/inventory/analytics/summary/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('total_categories', res.data)
        
        # 2. Availability
        res = self.client.get('/api/inventory/analytics/availability/')
        self.assertEqual(res.status_code, 200)
        
        # 3. Assets
        res = self.client.get('/api/inventory/analytics/assets/')
        self.assertEqual(res.status_code, 200)
        
        # 4. Maintenance
        res = self.client.get('/api/inventory/analytics/maintenance/')
        self.assertEqual(res.status_code, 200)
        
        # 5. Occupancy
        res = self.client.get('/api/inventory/analytics/occupancy/')
        self.assertEqual(res.status_code, 200)
        
        # 6. Reports
        res = self.client.get('/api/inventory/analytics/reports/')
        self.assertEqual(res.status_code, 200)


