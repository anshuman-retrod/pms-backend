from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant
from apps.accounts.models import AppUser
from apps.crm.models import GuestProfile, GuestContact
from apps.compliance.models import ConsentRecord, RetentionPolicy, GDPRRequest

class ComplianceAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Compliance Tenant', subdomain='compliance', country='India', currency='INR', timezone='UTC'
        )
        self.user = AppUser.objects.create_user(
            email='admin@compliance.com', password='Password123', tenant=self.tenant, name='Admin', username='compadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='compliance')
        self.client.force_authenticate(user=self.user)

        self.guest = GuestProfile.objects.create(
            tenant=self.tenant,
            first_name='John',
            last_name='Doe'
        )
        self.guest_contact = GuestContact.objects.create(
            tenant=self.tenant,
            guest=self.guest,
            email='john@doe.com',
            phone='+123456789'
        )

    def test_consent_record_lifecycle(self):
        # Create consent
        response = self.client.post('/api/compliance/consents/', {
            'guest': str(self.guest.id),
            'consent_type': 'MARKETING',
            'granted': True
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['granted'])

        # List consents
        list_res = self.client.get('/api/compliance/consents/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.data), 1)

    def test_retention_policy(self):
        # Create retention policy
        response = self.client.post('/api/compliance/retention-policies/', {
            'entity_name': 'RESERVATION',
            'retention_days': 730,
            'archive_enabled': True
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['retention_days'], 730)

        # Get policies
        list_res = self.client.get('/api/compliance/retention-policies/')
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(p['entity_name'] == 'RESERVATION' for p in list_res.data))

    def test_gdpr_request_lifecycle(self):
        # Create request
        response = self.client.post('/api/compliance/gdpr-request/', {
            'guest': str(self.guest.id),
            'request_type': 'EXPORT',
            'status': 'PENDING'
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['request_type'], 'EXPORT')

        # List requests
        list_res = self.client.get('/api/compliance/gdpr-request/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(len(list_res.data), 1)

    def test_data_exports(self):
        # Export tenant
        tenant_res = self.client.post('/api/compliance/export-tenant/')
        self.assertEqual(tenant_res.status_code, 202)
        self.assertIn('download_url', tenant_res.data)

        # Export guest
        guest_res = self.client.post('/api/compliance/export-guest/', {
            'guest_id': str(self.guest.id)
        }, format='json')
        self.assertEqual(guest_res.status_code, 202)
        self.assertIn('download_url', guest_res.data)
