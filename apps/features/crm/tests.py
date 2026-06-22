from django.test import TestCase
from django.utils import timezone
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.core.tenants.models import Tenant, Property
from apps.features.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)
from apps.features.crm.services import (
    GuestMergeService, LoyaltyService, DocumentVerificationService,
    GuestSearchEngine, TaggingService, EncryptionHelper
)
from apps.core.rbac.models import Permission, Role, UserPropertyRole

User = get_user_model()

class GuestCrmDomainTests(APITestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_1 = Tenant.objects.create(
            name='Tenant One', subdomain='t1', country='India', currency='INR', timezone='UTC'
        )
        self.tenant_2 = Tenant.objects.create(
            name='Tenant Two', subdomain='t2', country='India', currency='INR', timezone='UTC'
        )

        # Create Property for RBAC
        self.prop_t1 = Property.objects.create(
            tenant=self.tenant_1, name='Prop T1', address_line_1='A', city='Delhi',
            state='Delhi', country='India', postal_code='1', contact_email='a@t1.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )

        # Users and RBAC
        self.user_t1 = User.objects.create_user(
            email='t1_crm_staff@test.com', password='Password123', tenant=self.tenant_1,
            name='T1 CRM Staff', username='t1_crm_staff'
        )
        self.role_manage = Role.objects.create(
            tenant=self.tenant_1, code='crm_manager', name='CRM Manager'
        )
        
        # Permissions setup
        self.perm_view = Permission.objects.create(code='guest.view', category='crm')
        self.perm_create = Permission.objects.create(code='guest.create', category='crm')
        self.perm_edit = Permission.objects.create(code='guest.edit', category='crm')
        self.perm_delete = Permission.objects.create(code='guest.delete', category='crm')
        self.perm_merge = Permission.objects.create(code='guest.merge', category='crm')
        self.perm_verify = Permission.objects.create(code='guest.verify_document', category='crm')
        self.perm_loyalty = Permission.objects.create(code='guest.manage_loyalty', category='crm')
        self.perm_tags = Permission.objects.create(code='guest.manage_tags', category='crm')

        for perm in [self.perm_view, self.perm_create, self.perm_edit, self.perm_delete, self.perm_merge, self.perm_verify, self.perm_loyalty, self.perm_tags]:
            self.role_manage.permissions.create(role=self.role_manage, permission=perm)

        UserPropertyRole.objects.create(
            tenant=self.tenant_1, user=self.user_t1, property=self.prop_t1, role=self.role_manage
        )

        # Mock Profiles for Tenant 1
        self.john_t1 = GuestProfile.objects.create(
            tenant=self.tenant_1, first_name='John', last_name='Doe', loyalty_points=200
        )
        self.john_duplicate = GuestProfile.objects.create(
            tenant=self.tenant_1, first_name='John', last_name='Doe Duplicate', loyalty_points=500
        )

    def test_tenant_isolation(self):
        # Tenant 2 profile
        jane_t2 = GuestProfile.objects.create(
            tenant=self.tenant_2, first_name='Jane', last_name='Smith', loyalty_points=0
        )
        
        # A tenant cannot see or modify other tenant's profiles
        self.client.force_authenticate(user=self.user_t1)
        response = self.client.get('/api/crm/guests/', HTTP_X_PROPERTY_ID=str(self.prop_t1.id), HTTP_X_TENANT_SUBDOMAIN='t1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return only John Doe profiles of Tenant 1
        self.assertEqual(len(response.data), 2)
        
        # Cross-tenant save validation check
        with self.assertRaises(ValidationError):
            invalid_contact = GuestContact(
                tenant=self.tenant_1, guest=jane_t2, email='jane@t2.com', phone='1234'
            )
            invalid_contact.full_clean()

    def test_guest_profile_merge(self):
        # Add a preference to the duplicate
        pref = GuestPreference.objects.create(
            tenant=self.tenant_1, guest=self.john_duplicate, preference_category='ROOM',
            preference_key='pillow', preference_value='feather'
        )

        # Merge
        merged = GuestMergeService.merge_profiles(self.tenant_1, self.john_t1, self.john_duplicate)
        
        # Check duplicate profile becomes inactive and links to master
        self.john_duplicate.refresh_from_db()
        self.assertFalse(self.john_duplicate.is_active)
        self.assertEqual(self.john_duplicate.master_guest, self.john_t1)

        # Check points aggregations (200 + 500 = 700)
        self.john_t1.refresh_from_db()
        self.assertEqual(self.john_t1.loyalty_points, 700)

        # Check preference is re-linked
        pref.refresh_from_db()
        self.assertEqual(pref.guest, self.john_t1)

        # Check redirect resolution
        resolved = GuestMergeService.resolve_profile(self.john_duplicate)
        self.assertEqual(resolved, self.john_t1)

    def test_document_verification_and_encryption(self):
        # Create doc with unencrypted number initially
        raw_num = 'DL-987654321'
        encrypted_num = EncryptionHelper.encrypt(raw_num)
        
        doc = GuestDocument.objects.create(
            tenant=self.tenant_1, guest=self.john_t1, document_type='DRIVING_LICENCE',
            document_number=encrypted_num
        )
        self.assertEqual(doc.document_number, encrypted_num)
        self.assertEqual(EncryptionHelper.decrypt(doc.document_number), raw_num)

        # Verify
        DocumentVerificationService.verify_document(self.tenant_1, doc)
        doc.refresh_from_db()
        self.assertTrue(doc.is_verified)

        # Check timeline logs
        activities = GuestActivity.objects.filter(guest=self.john_t1, activity_type='DOCUMENT_VERIFIED')
        self.assertTrue(activities.exists())

    def test_loyalty_points_tier_evaluations(self):
        # STANDARD: < 1000
        self.assertEqual(LoyaltyService.evaluate_tier(500), 'STANDARD')
        # BRONZE: 1000 - 2999
        self.assertEqual(LoyaltyService.evaluate_tier(1500), 'BRONZE')
        # SILVER: 3000 - 5999
        self.assertEqual(LoyaltyService.evaluate_tier(4000), 'SILVER')
        # GOLD: 6000 - 9999
        self.assertEqual(LoyaltyService.evaluate_tier(8000), 'GOLD')
        # PLATINUM: 10000+
        self.assertEqual(LoyaltyService.evaluate_tier(12000), 'PLATINUM')

        # Add points check
        LoyaltyService.add_points(self.tenant_1, self.john_t1, 1000, "Stay completion")
        self.john_t1.refresh_from_db()
        self.assertEqual(self.john_t1.loyalty_points, 1200) # 200 + 1000 = 1200
        self.assertEqual(self.john_t1.loyalty_tier, 'BRONZE')

    def test_tag_assignments(self):
        tag = GuestTag.objects.create(tenant=self.tenant_1, code='VIP_GUEST', name='VIP Guest')
        TaggingService.assign_tag(self.tenant_1, self.john_t1, 'VIP_GUEST')
        
        self.assertTrue(self.john_t1.profile_tags.filter(tag=tag).exists())

    def test_guest_search(self):
        # Create contact details for John
        GuestContact.objects.create(
            tenant=self.tenant_1, guest=self.john_t1, email='johndoe@test.com', phone='+12345'
        )

        results = GuestSearchEngine.search_guests(self.tenant_1, query_str='johndoe')
        self.assertIn(self.john_t1, results)

    def test_timeline_integrity_write_only(self):
        act = GuestActivity.objects.create(
            tenant=self.tenant_1, guest=self.john_t1, activity_type='COMPLAINT',
            description='Room was too cold.'
        )

        # Update should fail
        with self.assertRaises(ValidationError):
            act.description = 'Updated description'
            act.save()

        # Delete should fail
        with self.assertRaises(ValidationError):
            act.delete()

        # QuerySet update/delete should fail
        with self.assertRaises(ValidationError):
            GuestActivity.objects.filter(id=act.id).update(description='No way')

        with self.assertRaises(ValidationError):
            GuestActivity.objects.filter(id=act.id).delete()
