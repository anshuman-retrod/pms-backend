from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.accounts.models import AppUser
from apps.tenants.models import Tenant, Property
from apps.crm.models import GuestProfile, GuestContact
from apps.reference.models import Country, ReservationSource
from apps.inventory.models import InventoryUnit, InventoryUnitType
from apps.rates.models import RatePlan, RatePlanVersion
from apps.reservations.models import (
    CorporateAccount, GroupBlock, Reservation, ReservationInventory,
    ReservationEvent, ReservationRateSnapshot
)
from apps.reservations.services import BookingEngine, RoomAssignmentEngine, CheckInCheckOutEngine

class ReservationEngineTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # Setup base Tenant and Property
        cls.tenant = Tenant.objects.create(
            name="Alpha Grand", subdomain="alphagrand", status="active",
            country="US", currency="USD", timezone="UTC"
        )
        cls.property = Property.objects.create(
            tenant=cls.tenant, name="Alpha Hotel", property_type="hotel",
            address_line_1="100 Main St", city="NYC", state="NY", country="US",
            postal_code="10001", contact_email="alpha@hotel.com", contact_phone="123",
            currency="USD", timezone="UTC"
        )

        # Users
        cls.superuser = AppUser.objects.create_superuser(
            username="adminuser", email="admin@alpha.com", password="password", tenant=cls.tenant
        )
        cls.staff_user = AppUser.objects.create_user(
            username="staffuser", email="staff@alpha.com", password="password", tenant=cls.tenant
        )

        # CRM profile
        cls.guest = GuestProfile.objects.create(
            tenant=cls.tenant, first_name="Alice", last_name="Smith",
            preferred_language="en", guest_type="DOMESTIC"
        )
        cls.contact = GuestContact.objects.create(
            tenant=cls.tenant, guest=cls.guest, email="alice@test.com", phone="+19999", is_primary=True
        )

        from apps.inventory.models import InventoryUnitCategory
        cls.category = InventoryUnitCategory.objects.create(
            tenant=cls.tenant, code="ROOM", name="Room Category", is_system=True
        )

        # Inventory Setup
        cls.deluxe_type = InventoryUnitType.objects.create(
            tenant=cls.tenant, property=cls.property, category=cls.category, code="DLX", name="Deluxe Room",
            base_occupancy=2, max_occupancy=4, is_sellable=True
        )
        cls.suite_type = InventoryUnitType.objects.create(
            tenant=cls.tenant, property=cls.property, category=cls.category, code="SUI", name="Luxury Suite",
            base_occupancy=2, max_occupancy=4, is_sellable=True
        )
        cls.room101 = InventoryUnit.objects.create(
            tenant=cls.tenant, property=cls.property, inventory_unit_type=cls.deluxe_type,
            name="Room 101", floor="1", operational_status="operational"
        )
        cls.room202 = InventoryUnit.objects.create(
            tenant=cls.tenant, property=cls.property, inventory_unit_type=cls.suite_type,
            name="Suite 202", floor="2", operational_status="operational"
        )

        # Rates setup
        from apps.rates.models import CancellationPolicy, ChildPolicy
        cls.cancel_policy = CancellationPolicy.objects.create(
            tenant=cls.tenant, code="FLEX", name="Flexible Cancellation",
            free_cancellation_hours=24, penalty_type="PERCENTAGE", penalty_value=Decimal("100.00")
        )
        cls.child_policy = ChildPolicy.objects.create(
            tenant=cls.tenant, code="KIDS", name="Kids Free Under 5",
            max_free_age=5, charge_age_from=6, charge_age_to=12, child_flat_charge=Decimal("20.00")
        )
        cls.rate_plan = RatePlan.objects.create(
            tenant=cls.tenant, property=cls.property, code="BAR", name="Best Available Rate",
            category="BAR", cancellation_policy=cls.cancel_policy, child_policy=cls.child_policy
        )
        cls.rate_version = RatePlanVersion.objects.create(
            rate_plan=cls.rate_plan, version_number=1, snapshot={}, effective_from=timezone.now()
        )

        # Reference
        cls.source_direct = ReservationSource.objects.create(code="direct", name="Direct")
        cls.country_us = Country.objects.create(code="US", name="United States")

        # Corporate
        cls.corp_account = CorporateAccount.objects.create(
            tenant=cls.tenant, company_name="Globex Corp", negotiated_rate_code="CORP_GLB",
            credit_limit=Decimal("10000.00"), is_active=True
        )

        # Group Block
        cls.group_block = GroupBlock.objects.create(
            tenant=cls.tenant, property=cls.property, name="wedding_block", block_type="Wedding Block",
            cutoff_date=timezone.now().date() + timezone.timedelta(days=10), status="OPEN",
            total_rooms=5, contracted_revenue=Decimal("1000.00")
        )

    def setUp(self):
        self.client.credentials(HTTP_X_TENANT_SUBDOMAIN=self.tenant.subdomain)
        self.client.force_authenticate(user=self.superuser)

    def test_create_multi_room_direct_booking(self):
        url = reverse('reservation-list')
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=3)

        data = {
            'primary_guest_id': str(self.guest.id),
            'reservation_source_id': str(self.source_direct.id),
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'origin_country_id': str(self.country_us.id),
            'arrival_date': arrival.isoformat(),
            'departure_date': departure.isoformat(),
            'booking_reference': 'TEST-MULT-111',
            'allocations': [
                {
                    'inventory_unit_type_id': str(self.deluxe_type.id),
                    'check_in_date': arrival.isoformat(),
                    'check_out_date': departure.isoformat(),
                    'adult_count': 2,
                    'child_count': 0,
                    'infant_count': 0,
                    'rate_plan_id': str(self.rate_plan.id),
                    'nightly_rates': [
                        {
                            'date': arrival.isoformat(),
                            'amount': '150.00',
                            'rate_plan_version_id': str(self.rate_version.id)
                        },
                        {
                            'date': (arrival + timezone.timedelta(days=1)).isoformat(),
                            'amount': '150.00',
                            'rate_plan_version_id': str(self.rate_version.id)
                        }
                    ]
                }
            ]
        }

        # Send query parameter to satisfy view property context validation
        response = self.client.post(f"{url}?property_id={self.property.id}", data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('confirmation_number' in response.data)
        
        # Verify Snapshots exist
        reservation = Reservation.objects.get(confirmation_number=response.data['confirmation_number'])
        self.assertEqual(reservation.total_amount, Decimal('300.00'))
        self.assertEqual(reservation.room_allocations.count(), 1)
        
        allocation = reservation.room_allocations.first()
        self.assertEqual(allocation.rate_snapshots.count(), 2)
        self.assertEqual(allocation.guests.count(), 1)
        self.assertTrue(allocation.guests.first().is_primary)

    def test_group_block_pickup_increments(self):
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=2)

        booking_data = {
            'primary_guest_id': self.guest.id,
            'reservation_source_id': self.source_direct.id,
            'group_block_id': self.group_block.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Group',
            'arrival_date': arrival,
            'departure_date': departure,
            'allocations': [
                {
                    'inventory_unit_type_id': self.deluxe_type.id,
                    'check_in_date': arrival,
                    'check_out_date': departure,
                    'rate_plan_id': self.rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival,
                            'amount': Decimal('120.00'),
                            'rate_plan_version_id': self.rate_version.id
                        }
                    ]
                }
            ]
        }

        self.group_block.refresh_from_db()
        self.assertEqual(self.group_block.pickup_rooms, 0)

        # Create booking via service directly
        res = BookingEngine.create_booking(self.tenant, self.property, booking_data, user=self.superuser)
        
        self.group_block.refresh_from_db()
        self.assertEqual(self.group_block.pickup_rooms, 1)

    def test_room_assignment_upgrade_logged(self):
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=2)

        booking_data = {
            'primary_guest_id': self.guest.id,
            'reservation_source_id': self.source_direct.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'arrival_date': arrival,
            'departure_date': departure,
            'allocations': [
                {
                    'inventory_unit_type_id': self.deluxe_type.id,
                    'check_in_date': arrival,
                    'check_out_date': departure,
                    'rate_plan_id': self.rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival,
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': self.rate_version.id
                        }
                    ]
                }
            ]
        }

        res = BookingEngine.create_booking(self.tenant, self.property, booking_data, user=self.superuser)
        allocation = res.room_allocations.first()

        # Try upgrade assignment without reason (should raise ValidationError)
        with self.assertRaises(ValidationError):
            RoomAssignmentEngine.assign_room(self.tenant, allocation.id, self.room202.id, user=self.superuser)

        # Assign upgrade with reason
        updated_alloc = RoomAssignmentEngine.assign_room(
            self.tenant, allocation.id, self.room202.id, user=self.superuser, upgrade_reason="Overbooked Deluxe"
        )
        self.assertEqual(updated_alloc.status, 'ASSIGNED')
        self.assertEqual(updated_alloc.upgrade_from_inventory_type, self.deluxe_type)
        self.assertEqual(updated_alloc.upgrade_reason, "Overbooked Deluxe")

    def test_timeline_append_only(self):
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=2)
        booking_data = {
            'primary_guest_id': self.guest.id,
            'reservation_source_id': self.source_direct.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'arrival_date': arrival,
            'departure_date': departure,
            'allocations': []
        }
        res = BookingEngine.create_booking(self.tenant, self.property, booking_data, user=self.superuser)

        event = ReservationEvent.objects.create(
            tenant=self.tenant,
            reservation=res,
            event_type='TEST_LOG',
            description='Test append timeline log'
        )
        self.assertTrue(ReservationEvent.objects.filter(id=event.id).exists())

        # Updates are blocked
        with self.assertRaises(ValidationError):
            event.description = "Updated desc"
            event.save()

        # Deletes are blocked
        with self.assertRaises(ValidationError):
            event.delete()

    def test_check_out_outstanding_balance_blocked(self):
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=2)

        booking_data = {
            'primary_guest_id': self.guest.id,
            'reservation_source_id': self.source_direct.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'arrival_date': arrival,
            'departure_date': departure,
            'allocations': [
                {
                    'inventory_unit_type_id': self.deluxe_type.id,
                    'check_in_date': arrival,
                    'check_out_date': departure,
                    'rate_plan_id': self.rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival,
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': self.rate_version.id
                        }
                    ]
                }
            ]
        }

        res = BookingEngine.create_booking(self.tenant, self.property, booking_data, user=self.superuser)
        allocation = res.room_allocations.first()

        # Assign room
        RoomAssignmentEngine.assign_room(self.tenant, allocation.id, self.room101.id, user=self.superuser)

        # Check-In
        CheckInCheckOutEngine.check_in(self.tenant, res.id, user=self.superuser)
        res.refresh_from_db()
        self.assertEqual(res.status, 'CHECKED_IN')

        # Try Check-Out when outstanding balance is present (amount = 150 + tax > paid = 0)
        with self.assertRaises(ValidationError):
            CheckInCheckOutEngine.check_out(self.tenant, res.id, user=self.superuser)

        # Pay balance
        res.paid_amount = res.balance_amount
        res.balance_amount = Decimal('0.00')
        res.save()

        # Check-Out succeeds
        CheckInCheckOutEngine.check_out(self.tenant, res.id, user=self.superuser)
        res.refresh_from_db()
        self.assertEqual(res.status, 'CHECKED_OUT')

    def test_reservation_enhancements(self):
        arrival = timezone.now().date() + timezone.timedelta(days=1)
        departure = timezone.now().date() + timezone.timedelta(days=2)

        # 1. Create a multi-room booking for Split Reservation testing
        booking_data = {
            'primary_guest_id': self.guest.id,
            'reservation_source_id': self.source_direct.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'arrival_date': arrival,
            'departure_date': departure,
            'allocations': [
                {
                    'inventory_unit_type_id': self.deluxe_type.id,
                    'check_in_date': arrival,
                    'check_out_date': departure,
                    'rate_plan_id': self.rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival,
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': self.rate_version.id
                        }
                    ]
                },
                {
                    'inventory_unit_type_id': self.deluxe_type.id,
                    'check_in_date': arrival,
                    'check_out_date': departure,
                    'rate_plan_id': self.rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival,
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': self.rate_version.id
                        }
                    ]
                }
            ]
        }

        res = BookingEngine.create_booking(self.tenant, self.property, booking_data, user=self.superuser)
        self.assertEqual(res.room_allocations.count(), 2)

        # Split
        alloc_to_split = res.room_allocations.first()
        self.client.force_authenticate(user=self.superuser)
        split_res = self.client.post(f'/api/reservations/bookings/{res.id}/split/', {
            'allocation_ids': [str(alloc_to_split.id)]
        }, format='json')
        self.assertEqual(split_res.status_code, 200)
        self.assertEqual(res.room_allocations.count(), 1) # parent has 1 left

        # 2. Re-instate
        # Cancel parent first
        self.client.post(f'/api/reservations/bookings/{res.id}/cancel/', {
            'cancellation_reason': 'Test Cancel'
        }, format='json')
        res.refresh_from_db()
        self.assertEqual(res.status, 'CANCELLED')

        # Reinstate
        reinstate_res = self.client.post(f'/api/reservations/bookings/{res.id}/reinstate/', {}, format='json')
        self.assertEqual(reinstate_res.status_code, 200)
        res.refresh_from_db()
        self.assertEqual(res.status, 'CONFIRMED')

        # 3. Room Upgrade & Change Room
        alloc = res.room_allocations.first()
        upgrade_res = self.client.post(f'/api/reservations/bookings/{res.id}/upgrade-room/', {
            'allocation_id': str(alloc.id),
            'new_inventory_type_id': str(self.suite_type.id),
            'upgrade_reason': 'VVIP upgrade'
        }, format='json')
        self.assertEqual(upgrade_res.status_code, 200)
        alloc.refresh_from_db()
        self.assertEqual(alloc.inventory_unit_type, self.suite_type)

        # Room change
        change_res = self.client.post(f'/api/reservations/bookings/{res.id}/change-room/', {
            'allocation_id': str(alloc.id),
            'new_room_id': str(self.room202.id)
        }, format='json')
        self.assertEqual(change_res.status_code, 200)
        alloc.refresh_from_db()
        self.assertEqual(alloc.inventory_unit, self.room202)

        # 4. Validate endpoints
        self.assertEqual(self.client.post('/api/reservations/bookings/validate-availability/', {}).status_code, 200)
        self.assertEqual(self.client.post('/api/reservations/bookings/validate-pricing/', {}).status_code, 200)
        self.assertEqual(self.client.post('/api/reservations/bookings/validate-restrictions/', {}).status_code, 200)

