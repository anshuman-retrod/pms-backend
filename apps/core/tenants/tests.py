from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from apps.core.tenants.models import Tenant
from apps.core.tenants.middleware import TenantResolutionMiddleware

class TenantResolutionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.active_tenant = Tenant.objects.create(
            name='Active Tenant',
            subdomain='active',
            status='active',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.suspended_tenant = Tenant.objects.create(
            name='Suspended Tenant',
            subdomain='suspended',
            status='suspended',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.terminated_tenant = Tenant.objects.create(
            name='Terminated Tenant',
            subdomain='terminated',
            status='terminated',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.middleware = TenantResolutionMiddleware(get_response=lambda r: JsonResponse({'status': 'ok'}))

    def test_resolution_by_header(self):
        request = self.factory.get('/api/users/', HTTP_X_TENANT_SUBDOMAIN='active')
        response = self.middleware(request)
        
        self.assertEqual(request.tenant, self.active_tenant)
        self.assertEqual(response.status_code, 200)

    def test_resolution_by_query_param(self):
        request = self.factory.get('/api/users/?subdomain=active')
        response = self.middleware(request)
        
        self.assertEqual(request.tenant, self.active_tenant)
        self.assertEqual(response.status_code, 200)

    def test_resolution_by_host_subdomain(self):
        # host matches active.domain.com
        request = self.factory.get('/api/users/', HTTP_HOST='active.domain.com')
        response = self.middleware(request)
        
        self.assertEqual(request.tenant, self.active_tenant)
        self.assertEqual(response.status_code, 200)

    def test_suspended_tenant(self):
        request = self.factory.get('/api/users/', HTTP_X_TENANT_SUBDOMAIN='suspended')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 403)
        self.assertTrue('suspended' in response.content.decode('utf-8'))

    def test_unknown_tenant(self):
        request = self.factory.get('/api/users/', HTTP_X_TENANT_SUBDOMAIN='unknown')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 404)
