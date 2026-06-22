from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.core.accounts.models import AppUser
from apps.core.tenants.models import Tenant, Property
from apps.core.reference.models import Country, Nationality, Language, Currency, DocumentType, ReservationSource

class ReferenceDataTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # Create standard Tenant and Property
        cls.tenant = Tenant.objects.create(
            name="Test Tenant",
            subdomain="testtenant",
            status="active",
            country="US",
            currency="USD",
            timezone="UTC"
        )
        cls.property = Property.objects.create(
            tenant=cls.tenant,
            name="Test Hotel",
            property_type="hotel",
            address_line_1="123 main st",
            city="NYC",
            state="NY",
            country="US",
            postal_code="10001",
            contact_email="test@hotel.com",
            contact_phone="123456",
            currency="USD",
            timezone="UTC"
        )

        # Create Users
        cls.superuser = AppUser.objects.create_superuser(
            username="adminuser",
            email="admin@test.com",
            password="adminpassword",
            tenant=cls.tenant
        )
        cls.staff_user = AppUser.objects.create_user(
            username="staffuser",
            email="staff@test.com",
            password="staffpassword",
            tenant=cls.tenant
        )

        # Seed basic records for testing
        cls.us_country = Country.objects.create(code="US", name="United States", phone_code="+1", is_active=True)
        cls.in_country = Country.objects.create(code="IN", name="India", phone_code="+91", is_active=False)
        cls.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", is_active=True)

    def setUp(self):
        # Enforce subdomain header for tenant middleware
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN=self.tenant.subdomain)

    def test_authenticated_user_can_read_countries(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('country-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We created 2 countries in setUpTestData
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_user_cannot_read_countries(self):
        url = reverse('country-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_user_cannot_write_countries(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('country-list')
        data = {"code": "CA", "name": "Canada", "phone_code": "+1"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_can_write_countries(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse('country-list')
        data = {"code": "CA", "name": "Canada", "phone_code": "+1"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Country.objects.filter(code="CA").exists())

    def test_search_parameter_filter(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('country-list')
        
        # Search for "India"
        response = self.client.get(url, {'search': 'India'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'IN')

        # Search for code "US"
        response = self.client.get(url, {'search': 'US'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'US')

    def test_is_active_filter(self):
        self.client.force_authenticate(user=self.staff_user)
        url = reverse('country-list')
        
        # Filter for active only
        response = self.client.get(url, {'is_active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'US')

        # Filter for inactive only
        response = self.client.get(url, {'is_active': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'IN')
