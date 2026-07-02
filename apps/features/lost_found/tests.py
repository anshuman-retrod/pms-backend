from django.utils import timezone
from rest_framework.test import APITestCase
from apps.core.tenants.models import Tenant, Property
from apps.core.accounts.models import AppUser
from apps.features.lost_found.models import LostFoundItem

class LostFoundAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Lost Tenant', subdomain='lostfound', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Lost', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='lost@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@lost.com', password='Password123', tenant=self.tenant, name='Admin', username='lostadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='lostfound')
        self.client.force_authenticate(user=self.user)

    def test_lost_found_workflows(self):
        # 1. Create Found Item
        response = self.client.post('/api/lost-found/items/', {
            'property': str(self.property.id),
            'item_type': 'FOUND',
            'item_name': 'iPhone 15',
            'description': 'Found near the swimming pool area.',
            'location_found': 'Pool Side',
            'reported_by': str(self.user.id),
            'status': 'REPORTED'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        item_id = response.data['id']

        # 2. Claim Item
        claim_res = self.client.post(f'/api/lost-found/items/{item_id}/claim/', {
            'claimed_by': 'John Doe'
        }, format='json')
        self.assertEqual(claim_res.status_code, 200)
        self.assertEqual(claim_res.data['status'], 'CLAIMED')
        self.assertEqual(claim_res.data['claimed_by'], 'John Doe')

        # 3. Create another found item to dispose
        response2 = self.client.post('/api/lost-found/items/', {
            'property': str(self.property.id),
            'item_type': 'FOUND',
            'item_name': 'Water Bottle',
            'description': 'Plastic bottle left in room 101.',
            'location_found': 'Room 101',
            'reported_by': str(self.user.id),
            'status': 'REPORTED'
        }, format='json')
        self.assertEqual(response2.status_code, 201)
        item_id2 = response2.data['id']

        # 4. Dispose Item
        dispose_res = self.client.post(f'/api/lost-found/items/{item_id2}/dispose/', {
            'disposed_reason': 'Recycled after 30 days.'
        }, format='json')
        self.assertEqual(dispose_res.status_code, 200)
        self.assertEqual(dispose_res.data['status'], 'DISPOSED')
        self.assertEqual(dispose_res.data['disposed_reason'], 'Recycled after 30 days.')
