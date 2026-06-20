from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant, Property
from apps.accounts.models import AppUser, LoginAttempt, AccountLock, UserSession, UserMFA
from apps.monitoring.models import SystemHealthSnapshot

class MonitoringAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Monitoring Tenant', subdomain='monitoring', country='India', currency='INR', timezone='UTC'
        )
        self.property = Property.objects.create(
            tenant=self.tenant, name='Hotel Monitor', address_line_1='Street', city='Goa',
            state='Goa', country='India', postal_code='403001', contact_email='monitor@test.com',
            contact_phone='+91', currency='INR', timezone='UTC'
        )
        # IsAdminUser requires is_staff=True
        self.admin_user = AppUser.objects.create_user(
            email='admin@monitoring.com', password='Password123', tenant=self.tenant, name='Admin', username='monitoradmin', is_staff=True
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='monitoring')
        
        # Create some mock records
        LoginAttempt.objects.create(user=self.admin_user, ip_address='127.0.0.1', success=False)
        AccountLock.objects.create(user=self.admin_user, locked_until=timezone.now() + timezone.timedelta(hours=1), reason='Too many attempts')
        UserSession.objects.create(user=self.admin_user, device='Test Device', ip='127.0.0.1', started_at=timezone.now(), last_seen_at=timezone.now())
        UserMFA.objects.create(user=self.admin_user, secret='secret', method='EMAIL', enabled=True)
        SystemHealthSnapshot.objects.create(service_name='Database', status='HEALTHY')

    def test_security_dashboard(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/security-dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['failed_logins'], 1)
        self.assertEqual(response.data['locked_accounts'], 1)
        self.assertEqual(response.data['active_sessions'], 1)
        self.assertEqual(response.data['mfa_enabled_users'], 1)

    def test_tenant_dashboard(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/tenant-dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_tenants', response.data)
        self.assertIn('active_properties', response.data)

    def test_system_health(self):
        # AllowAny
        response = self.client.get('/api/admin/system-health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ONLINE')
        self.assertEqual(len(response.data['snapshots']), 1)

    def test_system_usage(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/system-usage/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('api_calls', response.data)
        self.assertIn('occupancy_today', response.data)
