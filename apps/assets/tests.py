from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant, Property
from apps.accounts.models import AppUser
from apps.inventory.models import InventoryUnitCategory, InventoryUnitType, InventoryUnit
from apps.assets.models import Asset, AssetAssignment

class AssetAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Asset Tenant', subdomain='assets', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Asset', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='asset@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@assets.com', password='Password123', tenant=self.tenant, name='Admin', username='assetadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='assets')
        self.client.force_authenticate(user=self.user)

        # Inventory setup
        self.cat = InventoryUnitCategory.objects.create(tenant=self.tenant, code='room', name='Room')
        self.unit_type = InventoryUnitType.objects.create(
            tenant=self.tenant, property=self.property, category=self.cat, code='STD', name='Standard Room'
        )
        self.unit_1 = InventoryUnit.objects.create(
            tenant=self.tenant, property=self.property, inventory_unit_type=self.unit_type, name='101'
        )
        self.unit_2 = InventoryUnit.objects.create(
            tenant=self.tenant, property=self.property, inventory_unit_type=self.unit_type, name='102'
        )

    def test_asset_crud_and_assignment(self):
        # 1. Create Asset
        response = self.client.post('/api/assets/', {
            'property': str(self.property.id),
            'asset_code': 'TV-101',
            'asset_name': 'Living Room TV',
            'asset_type': 'TV',
            'serial_number': 'SN123456',
            'status': 'ACTIVE'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        asset_id = response.data['id']

        # 2. Assign Asset
        assign_res = self.client.post('/api/assets/assign/', {
            'asset_id': asset_id,
            'inventory_unit_id': str(self.unit_1.id)
        }, format='json')
        self.assertEqual(assign_res.status_code, 201)
        self.assertEqual(str(assign_res.data['inventory_unit']), str(self.unit_1.id))

        # 3. Transfer Asset
        transfer_res = self.client.post('/api/assets/transfer/', {
            'asset_id': asset_id,
            'new_inventory_unit_id': str(self.unit_2.id)
        }, format='json')
        self.assertEqual(transfer_res.status_code, 200)
        self.assertEqual(str(transfer_res.data['inventory_unit']), str(self.unit_2.id))

        # Check that old assignment is closed
        old_assignment = AssetAssignment.objects.filter(asset_id=asset_id, inventory_unit=self.unit_1).first()
        self.assertIsNotNone(old_assignment.removed_at)

        # 4. Unassign Asset
        unassign_res = self.client.post('/api/assets/unassign/', {
            'asset_id': asset_id
        }, format='json')
        self.assertEqual(unassign_res.status_code, 200)

        # Check no active assignments remain
        active_assignments = AssetAssignment.objects.filter(asset_id=asset_id, removed_at__isnull=True).count()
        self.assertEqual(active_assignments, 0)
