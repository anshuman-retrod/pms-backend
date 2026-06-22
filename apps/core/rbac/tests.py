from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from apps.core.tenants.models import Tenant, Property
from apps.core.rbac.models import Permission, Role, UserPropertyRole
from apps.core.rbac.decorators import require_property_access

User = get_user_model()

class RbacAndPropertyAccessTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            subdomain='test',
            status='active',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.property_allowed = Property.objects.create(
            tenant=self.tenant,
            name='Allowed Hotel',
            property_type='HOTEL',
            address_line_1='Allowed Street',
            city='Delhi',
            state='Delhi',
            country='India',
            postal_code='110001',
            contact_email='hotel1@test.com',
            contact_phone='+9111223344',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.property_blocked = Property.objects.create(
            tenant=self.tenant,
            name='Blocked Hotel',
            property_type='HOTEL',
            address_line_1='Blocked Street',
            city='Delhi',
            state='Delhi',
            country='India',
            postal_code='110001',
            contact_email='hotel2@test.com',
            contact_phone='+9111223344',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.user = User.objects.create_user(
            email='staff@test.com',
            password='Password123',
            tenant=self.tenant,
            name='Staff Member',
            username='staff'
        )
        self.role = Role.objects.create(
            tenant=self.tenant,
            code='desk_agent',
            name='Desk Agent'
        )
        
        # Link user to allowed property
        UserPropertyRole.objects.create(
            tenant=self.tenant,
            user=self.user,
            property=self.property_allowed,
            role=self.role
        )

        @require_property_access()
        def dummy_view(request, *args, **kwargs):
            return HttpResponse("Access Granted")
            
        self.view = dummy_view

    def test_property_access_granted(self):
        request = self.factory.get('/api/some-endpoint/')
        request.user = self.user
        request.tenant = self.tenant
        
        # Pass Property ID via header
        request.META['HTTP_X_PROPERTY_ID'] = str(self.property_allowed.id)
        
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), "Access Granted")

    def test_property_access_denied(self):
        request = self.factory.get('/api/some-endpoint/')
        request.user = self.user
        request.tenant = self.tenant
        
        # Pass Property ID that user doesn't have access to
        request.META['HTTP_X_PROPERTY_ID'] = str(self.property_blocked.id)
        
        response = self.view(request)
        self.assertEqual(response.status_code, 403)
        self.assertTrue('access' in response.content.decode('utf-8'))

    def test_superuser_access_bypass(self):
        superuser = User.objects.create_superuser(
            email='sys@test.com',
            password='Password123',
            name='Sysop',
            username='sysop'
        )
        request = self.factory.get('/api/some-endpoint/')
        request.user = superuser
        request.tenant = self.tenant
        request.META['HTTP_X_PROPERTY_ID'] = str(self.property_blocked.id)
        
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), "Access Granted")
