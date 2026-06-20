from django.test import TestCase
from django.utils import timezone
from datetime import timedelta, date
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.tenants.models import Tenant, Property
from apps.inventory.models import InventoryUnitCategory, InventoryUnitType, InventoryUnit
from apps.availability.models import InventoryAvailability, InventoryRestriction, InventoryHold
from apps.availability.services import (
    AvailabilityCalculationService,
    HoldService,
    RestrictionService,
    AvailabilityCalendarService
)
from apps.rbac.models import Permission, Role, UserPropertyRole

User = get_user_model()

class AvailabilityDomainTests(APITestCase):
    def setUp(self):
        # Create Tenants
        self.tenant_1 = Tenant.objects.create(
            name='Tenant One', subdomain='t1', country='India', currency='INR', timezone='UTC'
        )
        self.tenant_2 = Tenant.objects.create(
            name='Tenant Two', subdomain='t2', country='India', currency='INR', timezone='UTC'
        )

        # Create Properties
        self.prop_t1 = Property.objects.create(
            tenant=self.tenant_1, name='Prop T1', address_line_1='A', city='Delhi',
            state='Delhi', country='India', postal_code='1', contact_email='a@t1.com',
            contact_phone='1', currency='INR', timezone='UTC'
        )
        self.prop_t2 = Property.objects.create(
            tenant=self.tenant_2, name='Prop T2', address_line_1='B', city='Goa',
            state='Goa', country='India', postal_code='2', contact_email='b@t2.com',
            contact_phone='2', currency='INR', timezone='UTC'
        )

        # Category
        self.cat = InventoryUnitCategory.objects.create(
            tenant=None, code='room', name='System Room', is_system=True
        )

        # Unit Types
        self.unit_type_t1 = InventoryUnitType.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, category=self.cat,
            code='TYPE-T1', name='Type T1 Room'
        )
        self.unit_type_t2 = InventoryUnitType.objects.create(
            tenant=self.tenant_2, property=self.prop_t2, category=self.cat,
            code='TYPE-T2', name='Type T2 Room'
        )

        # Users and RBAC
        self.user_t1 = User.objects.create_user(
            email='t1_staff@test.com', password='Password123', tenant=self.tenant_1,
            name='T1 Staff', username='t1_staff'
        )
        self.superuser = User.objects.create_superuser(
            email='sys@test.com', password='Password123', name='Sysop', username='sysop'
        )

        self.role_manage = Role.objects.create(
            tenant=self.tenant_1, code='manager', name='Manager'
        )
        
        # Permissions setup
        self.perm_view = Permission.objects.create(code='availability.view', category='availability')
        self.perm_create = Permission.objects.create(code='availability.create', category='availability')
        self.perm_edit = Permission.objects.create(code='availability.edit', category='availability')
        self.perm_delete = Permission.objects.create(code='availability.delete', category='availability')
        self.perm_restriction = Permission.objects.create(code='restriction.manage', category='availability')
        self.perm_hold = Permission.objects.create(code='hold.manage', category='availability')

        for perm in [self.perm_view, self.perm_create, self.perm_edit, self.perm_delete, self.perm_restriction, self.perm_hold]:
            self.role_manage.permissions.create(role=self.role_manage, permission=perm)

        UserPropertyRole.objects.create(
            tenant=self.tenant_1, user=self.user_t1, property=self.prop_t1, role=self.role_manage
        )

    def test_tenant_isolation_availability(self):
        # A tenant cannot see or modify other tenant's availability records
        avail_t2 = InventoryAvailability.objects.create(
            tenant=self.tenant_2, property=self.prop_t2, date=date.today(),
            inventory_unit_type=self.unit_type_t2, allocated_count=5, sold_count=0,
            blocked_count=0, overbooking_limit=0
        )
        
        # Request from user in tenant_1 must not see tenant_2's records
        self.client.force_authenticate(user=self.user_t1)
        response = self.client.get('/api/availability/', HTTP_X_PROPERTY_ID=str(self.prop_t1.id), HTTP_X_TENANT_SUBDOMAIN='t1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be empty since t1 has no availability seeded yet
        self.assertEqual(len(response.data), 0)

        # Standard check: trying to create availability with property of another tenant fails validation
        with self.assertRaises(ValidationError):
            avail_invalid = InventoryAvailability(
                tenant=self.tenant_1, property=self.prop_t2, date=date.today(),
                inventory_unit_type=self.unit_type_t1, allocated_count=5
            )
            avail_invalid.full_clean()

    def test_availability_formula_calculation(self):
        # Setup: Allocated = 20, Overbooking = 2, Sold = 10, Blocked = 1
        d = date.today()
        avail = InventoryAvailability.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, allocated_count=20, sold_count=10,
            blocked_count=1, overbooking_limit=2
        )

        # 1. No active holds
        available = AvailabilityCalculationService.calculate_available(
            self.tenant_1, self.prop_t1.id, self.unit_type_t1.id, d,
            avail.allocated_count, avail.overbooking_limit, avail.sold_count, avail.blocked_count
        )
        # (20 + 2) - (10 + 1 + 0) = 11
        self.assertEqual(available, 11)

        # 2. Add an active hold of quantity 2
        hold = HoldService.create_hold(
            tenant=self.tenant_1, property=self.prop_t1, unit_type=self.unit_type_t1,
            expires_at=timezone.now() + timedelta(minutes=10), quantity=2, hold_type='CART'
        )

        available_with_hold = AvailabilityCalculationService.calculate_available(
            self.tenant_1, self.prop_t1.id, self.unit_type_t1.id, d,
            avail.allocated_count, avail.overbooking_limit, avail.sold_count, avail.blocked_count
        )
        # (20 + 2) - (10 + 1 + 2) = 9
        self.assertEqual(available_with_hold, 9)

        # 3. Release the hold
        HoldService.release_hold(hold)
        available_after_release = AvailabilityCalculationService.calculate_available(
            self.tenant_1, self.prop_t1.id, self.unit_type_t1.id, d,
            avail.allocated_count, avail.overbooking_limit, avail.sold_count, avail.blocked_count
        )
        self.assertEqual(available_after_release, 11)

    def test_hold_conversions_and_expiry(self):
        # Create hold
        hold = HoldService.create_hold(
            tenant=self.tenant_1, property=self.prop_t1, unit_type=self.unit_type_t1,
            expires_at=timezone.now() - timedelta(minutes=5), quantity=1, hold_type='CART'
        )
        self.assertEqual(hold.status, 'ACTIVE')

        # Test automatic expiry of holds
        expired_count = HoldService.expire_holds()
        self.assertEqual(expired_count, 1)
        
        hold.refresh_from_db()
        self.assertEqual(hold.status, 'RELEASED')

        # Test hold conversion
        hold2 = HoldService.create_hold(
            tenant=self.tenant_1, property=self.prop_t1, unit_type=self.unit_type_t1,
            expires_at=timezone.now() + timedelta(minutes=5), quantity=1, hold_type='CART'
        )
        HoldService.convert_hold(hold2)
        hold2.refresh_from_db()
        self.assertEqual(hold2.status, 'CONVERTED')

    def test_restrictions_checks(self):
        d = date.today()
        # STOP_SELL
        InventoryRestriction.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, restriction_type='STOP_SELL'
        )
        self.assertTrue(RestrictionService.is_stop_sell(self.tenant_1, self.prop_t1.id, d, self.unit_type_t1.id))

        # CTA
        InventoryRestriction.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, restriction_type='CTA'
        )
        self.assertTrue(RestrictionService.is_cta(self.tenant_1, self.prop_t1.id, d, self.unit_type_t1.id))

        # CTD
        InventoryRestriction.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, restriction_type='CTD'
        )
        self.assertTrue(RestrictionService.is_ctd(self.tenant_1, self.prop_t1.id, d, self.unit_type_t1.id))

        # MIN_LOS
        min_los = InventoryRestriction.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, restriction_type='MIN_LOS', restriction_value=3
        )
        valid, msg = RestrictionService.validate_min_los(self.tenant_1, self.prop_t1.id, d, 2, self.unit_type_t1.id)
        self.assertFalse(valid)
        
        valid, msg = RestrictionService.validate_min_los(self.tenant_1, self.prop_t1.id, d, 3, self.unit_type_t1.id)
        self.assertTrue(valid)

        # MAX_LOS
        max_los = InventoryRestriction.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, restriction_type='MAX_LOS', restriction_value=5
        )
        valid, msg = RestrictionService.validate_max_los(self.tenant_1, self.prop_t1.id, d, 6, self.unit_type_t1.id)
        self.assertFalse(valid)
        
        valid, msg = RestrictionService.validate_max_los(self.tenant_1, self.prop_t1.id, d, 4, self.unit_type_t1.id)
        self.assertTrue(valid)

    def test_bulk_update_api(self):
        self.client.force_authenticate(user=self.user_t1)
        d = date.today().isoformat()
        
        payload = {
            "property_id": str(self.prop_t1.id),
            "updates": [
                {
                    "date": d,
                    "inventory_unit_type_id": str(self.unit_type_t1.id),
                    "allocated_count": 15,
                    "sold_count": 2,
                    "blocked_count": 0,
                    "overbooking_limit": 1
                }
            ]
        }
        
        response = self.client.post('/api/availability/bulk-update/', payload, format='json', HTTP_X_PROPERTY_ID=str(self.prop_t1.id), HTTP_X_TENANT_SUBDOMAIN='t1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created_records'], 1)

        # Check database record
        avail = InventoryAvailability.objects.get(property=self.prop_t1, date=d, inventory_unit_type=self.unit_type_t1)
        self.assertEqual(avail.allocated_count, 15)

    def test_calendar_api(self):
        # Create availability record
        d = date.today()
        InventoryAvailability.objects.create(
            tenant=self.tenant_1, property=self.prop_t1, date=d,
            inventory_unit_type=self.unit_type_t1, allocated_count=10, sold_count=2,
            blocked_count=1, overbooking_limit=0
        )

        self.client.force_authenticate(user=self.user_t1)
        response = self.client.get(
            '/api/availability/calendar/',
            {
                'property_id': str(self.prop_t1.id),
                'start_date': d.isoformat(),
                'end_date': d.isoformat()
            },
            HTTP_X_PROPERTY_ID=str(self.prop_t1.id),
            HTTP_X_TENANT_SUBDOMAIN='t1'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['available_count'], 7) # 10 - 3 = 7
