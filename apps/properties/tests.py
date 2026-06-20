from django.test import TestCase
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant, Property
from apps.accounts.models import AppUser
from apps.properties.models import PropertyConfiguration, PropertyContact

class PropertyConfigAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Property Tenant', subdomain='property', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Test', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='property@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@property.com', password='Password123', tenant=self.tenant, name='Admin', username='propadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='property')
        self.client.force_authenticate(user=self.user)

    def test_property_configuration_crud(self):
        # 1. Create Property Configuration
        response = self.client.post('/api/property-configurations/', {
            'property': str(self.property.id),
            'timezone': 'Asia/Kolkata',
            'currency': 'INR',
            'language': 'en',
            'tax_profile': 'STANDARD',
            'fiscal_year_start': '04-01',
            'checkin_time': '14:00',
            'checkout_time': '11:00'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        config_id = response.data['id']

        # 2. Get list
        list_res = self.client.get('/api/property-configurations/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.data), 1)

        # 3. Update
        update_res = self.client.put(f'/api/property-configurations/{config_id}/', {
            'property': str(self.property.id),
            'timezone': 'Asia/Kolkata',
            'currency': 'INR',
            'language': 'en-in',
            'tax_profile': 'GST_18',
            'fiscal_year_start': '04-01',
            'checkin_time': '12:00',
            'checkout_time': '11:00'
        }, format='json')
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.data['language'], 'en-in')

    def test_property_contact_crud(self):
        # 1. Create Property Contact
        response = self.client.post('/api/property-contacts/', {
            'property': str(self.property.id),
            'phone': '+919999999999',
            'email': 'frontdesk@hotel.com',
            'website': 'https://hotel.com',
            'emergency_contact': '911'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        contact_id = response.data['id']

        # 2. Get list
        list_res = self.client.get('/api/property-contacts/')
        self.assertEqual(list_res.status_code, 200)

        # 3. Update
        update_res = self.client.put(f'/api/property-contacts/{contact_id}/', {
            'property': str(self.property.id),
            'phone': '+918888888888',
            'email': 'frontdesk@hotel.com',
            'website': 'https://hotel.com',
            'emergency_contact': '911'
        }, format='json')
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.data['phone'], '+918888888888')
