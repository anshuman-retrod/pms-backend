from django.test import TestCase
from rest_framework.test import APITestCase
from apps.core.common.models import SystemLanguage
from django.contrib.auth import get_user_model

User = get_user_model()

class SystemLanguageTests(APITestCase):
    def setUp(self):
        from apps.core.tenants.models import Tenant
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            subdomain='test',
            status='active',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.superuser = User.objects.create_superuser(
            email='admin@retrod.in',
            password='Password123',
            name='Sys Admin',
            username='sysadmin',
            tenant=self.tenant
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='test')
        self.client.force_authenticate(user=self.superuser)

    def test_language_crud(self):
        # Create
        response = self.client.post('/api/superadmin-languages/', {
            'name': 'Spanish',
            'code': 'es',
            'is_active': True,
            'is_default': False
        }, format='json')
        self.assertEqual(response.status_code, 201)
        lang_id = response.data['id']

        # List
        list_resp = self.client.get('/api/superadmin-languages/')
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(any(lang['name'] == 'Spanish' for lang in list_resp.data))

        # Delete
        del_resp = self.client.delete(f'/api/superadmin-languages/{lang_id}/')
        self.assertEqual(del_resp.status_code, 204)
