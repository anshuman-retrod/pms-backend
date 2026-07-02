from django.utils import timezone
from rest_framework.test import APITestCase
from apps.core.tenants.models import Tenant, Property
from apps.core.accounts.models import AppUser
from apps.features.inventory.models import InventoryUnitCategory, InventoryUnitType, InventoryUnit
from apps.features.linen.models import LinenItem, LinenAssignment, LaundryRecord

class LinenAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Linen Tenant', subdomain='linen', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Linen', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='linen@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@linen.com', password='Password123', tenant=self.tenant, name='Admin', username='linenadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='linen')
        self.client.force_authenticate(user=self.user)

        # Inventory setup
        self.cat = InventoryUnitCategory.objects.create(tenant=self.tenant, code='room', name='Room')
        self.unit_type = InventoryUnitType.objects.create(
            tenant=self.tenant, property=self.property, category=self.cat, code='STD', name='Standard Room'
        )
        self.unit_1 = InventoryUnit.objects.create(
            tenant=self.tenant, property=self.property, inventory_unit_type=self.unit_type, name='101'
        )

    def test_linen_crud_and_adjustment(self):
        # 1. Create Linen Item
        response = self.client.post('/api/linen/items/', {
            'property': str(self.property.id),
            'name': 'King Bed Sheet',
            'code': 'KBS-1',
            'total_qty': 100,
            'par_stock': 20,
            'status': 'ACTIVE'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        item_id = response.data['id']

        # 2. Adjust Stock
        adjust_res = self.client.post(f'/api/linen/items/{item_id}/adjust-stock/', {
            'quantity': 50
        }, format='json')
        self.assertEqual(adjust_res.status_code, 200)
        self.assertEqual(adjust_res.data['total_qty'], 150)

        # 3. Assign Linen to room
        assign_res = self.client.post('/api/linen/assignments/', {
            'linen_item': item_id,
            'inventory_unit': str(self.unit_1.id),
            'quantity': 4
        }, format='json')
        self.assertEqual(assign_res.status_code, 201)

        # 4. Create Laundry Record
        laundry_res = self.client.post('/api/linen/laundry/', {
            'property': str(self.property.id),
            'linen_item': item_id,
            'quantity_sent': 10,
            'sent_date': '2026-06-25',
            'expected_return_date': '2026-06-27',
            'status': 'SENT'
        }, format='json')
        self.assertEqual(laundry_res.status_code, 201)
        laundry_id = laundry_res.data['id']

        # 5. Receive Laundry
        receive_res = self.client.post(f'/api/linen/laundry/{laundry_id}/receive-laundry/', {
            'quantity': 10
        }, format='json')
        self.assertEqual(receive_res.status_code, 200)
        self.assertEqual(receive_res.data['status'], 'RETURNED')
