from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.tenants.models import Tenant
from apps.accounts.models import AppUser
from apps.subscriptions.models import (
    Product, SubscriptionPlan, SubscriptionEntitlement, TenantSubscription,
    ProductFeature, TenantProduct, TenantProductLicense, TenantProductEntitlement, TenantProductUsage
)

class SubscriptionAPITests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Test Tenant',
            subdomain='test',
            status='active',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.user = AppUser.objects.create_user(
            email='admin@test.com',
            password='Password123',
            tenant=self.tenant,
            name='Test Admin',
            username='testadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='test')
        self.client.force_authenticate(user=self.user)

        # Create products
        self.pms = Product.objects.create(code='PMS', name='Property Management System')
        self.pos = Product.objects.create(code='POS', name='Point of Sale')

        # Create plans
        self.plan_basic = SubscriptionPlan.objects.create(
            name='Basic', billing_cycle='MONTHLY', price=99.00, currency='USD'
        )
        self.plan_premium = SubscriptionPlan.objects.create(
            name='Premium', billing_cycle='MONTHLY', price=199.00, currency='USD'
        )

        # Create entitlements
        SubscriptionEntitlement.objects.create(
            plan=self.plan_basic, feature_code='ROOM_LIMIT', limit_type='NUMERIC', limit_value=50
        )
        SubscriptionEntitlement.objects.create(
            plan=self.plan_premium, feature_code='ROOM_LIMIT', limit_type='NUMERIC', limit_value=200
        )

    def test_products_list(self):
        response = self.client.get('/api/subscriptions/products/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_plans_list(self):
        response = self.client.get('/api/subscriptions/plans/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_assign_subscription(self):
        response = self.client.post('/api/subscriptions/assign/', {
            'plan_id': str(self.plan_basic.id)
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'ACTIVE')

        # Check usage API
        usage_res = self.client.get('/api/subscriptions/usage/')
        self.assertEqual(usage_res.status_code, 200)
        self.assertEqual(usage_res.data['active_plan'], 'Basic')
        self.assertEqual(usage_res.data['entitlements']['ROOM_LIMIT']['value'], 50)

    def test_upgrade_subscription(self):
        # Assign basic first
        self.client.post('/api/subscriptions/assign/', {'plan_id': str(self.plan_basic.id)}, format='json')

        # Upgrade to premium
        response = self.client.post('/api/subscriptions/upgrade/', {
            'plan_id': str(self.plan_premium.id)
        }, format='json')
        self.assertEqual(response.status_code, 200)

        # Verify usage updated
        usage_res = self.client.get('/api/subscriptions/usage/')
        self.assertEqual(usage_res.status_code, 200)
        self.assertEqual(usage_res.data['active_plan'], 'Premium')
        self.assertEqual(usage_res.data['entitlements']['ROOM_LIMIT']['value'], 200)

    def test_downgrade_subscription(self):
        # Assign premium first
        self.client.post('/api/subscriptions/assign/', {'plan_id': str(self.plan_premium.id)}, format='json')

        # Downgrade to basic
        response = self.client.post('/api/subscriptions/downgrade/', {
            'plan_id': str(self.plan_basic.id)
        }, format='json')
        self.assertEqual(response.status_code, 200)

        # Verify usage updated
        usage_res = self.client.get('/api/subscriptions/usage/')
        self.assertEqual(usage_res.status_code, 200)
        self.assertEqual(usage_res.data['active_plan'], 'Basic')


class ProductAccessEngineTests(APITestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name='Access Test Tenant',
            subdomain='access',
            status='active',
            country='India',
            currency='INR',
            timezone='Asia/Kolkata'
        )
        self.user = AppUser.objects.create_user(
            email='admin@access.com',
            password='Password123',
            tenant=self.tenant,
            name='Access Admin',
            username='accessadmin'
        )
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN='access')
        self.client.force_authenticate(user=self.user)

        # Products
        self.pms = Product.objects.create(code='PMS', name='Property Management System')
        self.crm = Product.objects.create(code='CRM', name='Guest CRM')

        # Active Tenant Subscription
        self.plan = SubscriptionPlan.objects.create(
            name='Test Plan', billing_cycle='MONTHLY', price=100.00, currency='USD'
        )
        self.sub = TenantSubscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status='ACTIVE'
        )

        # Features
        self.feature_reservations = ProductFeature.objects.create(
            product=self.pms,
            code='PMS.RESERVATIONS',
            name='Reservations Feature'
        )
        self.feature_crm_leads = ProductFeature.objects.create(
            product=self.crm,
            code='CRM.LEADS',
            name='CRM Leads'
        )

    def test_product_feature_crud(self):
        # Create product feature
        response = self.client.post('/api/product-features/', {
            'product': str(self.pms.id),
            'code': 'PMS.CHECKOUT',
            'name': 'Checkout Feature',
            'is_active': True
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['code'], 'PMS.CHECKOUT')

        # List features
        list_res = self.client.get('/api/product-features/')
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(f['code'] == 'PMS.CHECKOUT' for f in list_res.data))

    def test_nested_product_features(self):
        # GET nested feature list
        response = self.client.get(f'/api/products/{self.pms.id}/features/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['code'], 'PMS.RESERVATIONS')

        # POST nested feature
        post_res = self.client.post(f'/api/products/{self.pms.id}/features/', {
            'code': 'PMS.BILLING',
            'name': 'Billing Feature'
        }, format='json')
        self.assertEqual(post_res.status_code, 201)
        self.assertEqual(post_res.data['code'], 'PMS.BILLING')

    def test_tenant_product_assignment_and_license_lifecycle(self):
        # Assign PMS product to tenant
        response = self.client.post('/api/products/assign/', {
            'product_id': str(self.pms.id),
            'tenant_subscription_id': str(self.sub.id),
            'expires_days': 15
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ACTIVE')

        tenant_product_id = response.data['id']

        # Generate License
        lic_res = self.client.post('/api/licenses/create/', {
            'tenant_product_id': tenant_product_id,
            'start_date': str(timezone.now().date()),
            'end_date': str(timezone.now().date() + timezone.timedelta(days=15))
        }, format='json')
        self.assertEqual(lic_res.status_code, 201)
        license_key = lic_res.data['license_key']

        # Validate License
        val_res = self.client.post('/api/licenses/validate/', {'license_key': license_key}, format='json')
        self.assertEqual(val_res.status_code, 200)
        self.assertTrue(val_res.data['valid'])

        # Suspend License
        susp_res = self.client.post('/api/licenses/suspend/', {'license_key': license_key}, format='json')
        self.assertEqual(susp_res.status_code, 200)
        self.assertEqual(susp_res.data['status'], 'SUSPENDED')

        # Validate Suspended License (should fail/false)
        val_res2 = self.client.post('/api/licenses/validate/', {'license_key': license_key}, format='json')
        self.assertEqual(val_res2.status_code, 200)
        self.assertFalse(val_res2.data['valid'])

        # Reactivate License
        react_res = self.client.post('/api/licenses/reactivate/', {'license_key': license_key}, format='json')
        self.assertEqual(react_res.status_code, 200)
        self.assertEqual(react_res.data['status'], 'ACTIVE')

    def test_entitlements_and_usage_tracking(self):
        # Setup assigned product
        tp = TenantProduct.objects.create(
            tenant=self.tenant,
            product=self.pms,
            tenant_subscription=self.sub,
            activated_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=30),
            status='ACTIVE'
        )
        
        # Create Entitlement
        ent = TenantProductEntitlement.objects.create(
            tenant_product=tp,
            feature_code='MAX_ROOMS',
            limit_type='NUMERIC',
            limit_value_numeric=5
        )

        # Validate Limit within bounds (current = 3, limit = 5)
        val_res = self.client.post('/api/entitlements/validate/', {
            'feature_code': 'MAX_ROOMS',
            'current_value': 3
        }, format='json')
        self.assertEqual(val_res.status_code, 200)
        self.assertTrue(val_res.data['valid'])

        # Validate Limit exceeded bounds (current = 6, limit = 5)
        val_res2 = self.client.post('/api/entitlements/validate/', {
            'feature_code': 'MAX_ROOMS',
            'current_value': 6
        }, format='json')
        self.assertEqual(val_res2.status_code, 200)
        self.assertFalse(val_res2.data['valid'])

        # Create Usage Record
        usage = TenantProductUsage.objects.create(
            tenant_product=tp,
            metric_code='MAX_ROOMS',
            usage_value=2,
            usage_limit=5
        )

        # Get Usage Summary
        sum_res = self.client.get('/api/usage/summary/')
        self.assertEqual(sum_res.status_code, 200)
        self.assertEqual(len(sum_res.data), 1)
        self.assertEqual(sum_res.data[0]['metric_code'], 'MAX_ROOMS')
        self.assertEqual(sum_res.data[0]['usage_value'], 2)

    def test_recalculate_usage(self):
        # Setup assigned product
        tp = TenantProduct.objects.create(
            tenant=self.tenant,
            product=self.pms,
            tenant_subscription=self.sub,
            activated_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=30),
            status='ACTIVE'
        )
        usage = TenantProductUsage.objects.create(
            tenant_product=tp,
            metric_code='ROOMS_USED',
            usage_value=0,
            usage_limit=100
        )
        # Recalculate usage endpoint
        response = self.client.post('/api/usage/recalculate/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ROOMS_USED', response.data['results'])

    def test_soft_delete_and_subscription_expiry(self):
        # Setup assigned product
        tp = TenantProduct.objects.create(
            tenant=self.tenant,
            product=self.pms,
            tenant_subscription=self.sub,
            activated_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(days=30),
            status='ACTIVE'
        )
        license_obj = TenantProductLicense.objects.create(
            tenant_product=tp,
            license_key='LIC-EXP-TEST',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=30),
            status='ACTIVE'
        )

        # Soft delete / remove assignment
        response = self.client.post('/api/products/remove/', {'product_id': str(self.pms.id)}, format='json')
        self.assertEqual(response.status_code, 200)
        
        # Verify status became SUSPENDED
        tp.refresh_from_db()
        self.assertEqual(tp.status, 'SUSPENDED')
        
        license_obj.refresh_from_db()
        self.assertEqual(license_obj.status, 'SUSPENDED')

        # Test Subscription Expiry command
        tp.status = 'ACTIVE'
        tp.save()
        license_obj.status = 'ACTIVE'
        license_obj.save()
        
        # Backdate subscription to force expiry
        self.sub.end_date = timezone.now().date() - timezone.timedelta(days=1)
        self.sub.save()

        # Run command
        from django.core.management import call_command
        call_command('expire_subscriptions')

        tp.refresh_from_db()
        self.assertEqual(tp.status, 'EXPIRED')

        license_obj.refresh_from_db()
        self.assertEqual(license_obj.status, 'EXPIRED')


