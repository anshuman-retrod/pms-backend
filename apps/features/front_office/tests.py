from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.core.tenants.models import Tenant, Property
from apps.features.crm.models import GuestProfile
from apps.core.reference.models import Country, ReservationSource
from apps.features.inventory.models import InventoryUnitType, InventoryUnitCategory
from apps.features.rates.models import CancellationPolicy, ChildPolicy
from apps.features.reservations.models import Reservation, ReservationInventory
from apps.features.front_office.models import (
    GuestRegistrationCard, RoomKeyCard, GuestFolio, FolioTransaction,
    CashierShift, GuestDeposit, HouseAccount, NightAuditSession, ShiftHandover
)

class FrontOfficeModelsTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Hotel Biraj Group", subdomain="biraj")
        self.property = Property.objects.create(tenant=self.tenant, name="Main Wing")
        
        self.guest = GuestProfile.objects.create(
            tenant=self.tenant,
            first_name="Aarav",
            last_name="Sharma"
        )
        self.country = Country.objects.create(code="IN", name="India")
        self.source = ReservationSource.objects.create(code="DIRECT", name="Direct")
        
        self.cancellation_policy = CancellationPolicy.objects.create(
            tenant=self.tenant,
            code="STANDARD_48H",
            name="Standard 48 Hours"
        )
        self.child_policy = ChildPolicy.objects.create(
            tenant=self.tenant,
            code="FREE_UNDER_5",
            name="Free Under 5"
        )
        
        self.reservation = Reservation.objects.create(
            tenant=self.tenant,
            property=self.property,
            primary_guest=self.guest,
            reservation_source=self.source,
            booking_date=timezone.now().date(),
            arrival_date=timezone.now().date(),
            departure_date=timezone.now().date() + timedelta(days=2),
            confirmation_number="CONF10001",
            reservation_type="Transient",
            market_segment="LEISURE"
        )

        self.category = InventoryUnitCategory.objects.create(
            tenant=self.tenant,
            code="ROOM",
            name="Room"
        )

        self.unit_type = InventoryUnitType.objects.create(
            tenant=self.tenant,
            property=self.property,
            category=self.category,
            code="DLX-KING",
            name="Deluxe King"
        )

        self.alloc = ReservationInventory.objects.create(
            tenant=self.tenant,
            reservation=self.reservation,
            inventory_unit_type=self.unit_type,
            check_in_date=self.reservation.arrival_date,
            check_out_date=self.reservation.departure_date
        )

    def test_guest_registration_card_creation(self):
        reg = GuestRegistrationCard.objects.create(
            tenant=self.tenant,
            reservation=self.reservation,
            guest=self.guest,
            registration_number="REG20002",
            id_document_type="PASSPORT",
            id_document_number="Z1234567"
        )
        self.assertEqual(reg.registration_number, "REG20002")
        self.assertFalse(reg.is_verified)

    def test_room_key_card_creation(self):
        key = RoomKeyCard.objects.create(
            tenant=self.tenant,
            reservation_inventory=self.alloc,
            card_number="KEYCARD001",
            expires_at=timezone.now() + timedelta(days=2)
        )
        self.assertEqual(key.card_number, "KEYCARD001")
        self.assertEqual(key.status, "ACTIVE")

    def test_guest_folio_balance_calculation(self):
        folio = GuestFolio.objects.create(
            tenant=self.tenant,
            reservation=self.reservation,
            folio_number="FOLIO9901",
            total_charges=Decimal("350.00"),
            total_payments=Decimal("150.00")
        )
        self.assertEqual(folio.balance, Decimal("200.00"))

    def test_folio_transaction_validation(self):
        folio = GuestFolio.objects.create(
            tenant=self.tenant,
            reservation=self.reservation,
            folio_number="FOLIO9902"
        )
        tx = FolioTransaction.objects.create(
            tenant=self.tenant,
            folio=folio,
            transaction_type="CHARGE",
            charge_code="ROOM_CHARGE",
            amount=Decimal("120.00"),
            description="Room Charge Post"
        )
        self.assertEqual(tx.amount, Decimal("120.00"))

    def test_cashier_shift_creation(self):
        shift = CashierShift.objects.create(
            tenant=self.tenant,
            property=self.property,
            shift_code="AM_SHIFT",
            opening_balance=Decimal("200.00")
        )
        self.assertEqual(shift.shift_code, "AM_SHIFT")
        self.assertEqual(shift.status, "OPEN")

    def test_night_audit_session_creation(self):
        session = NightAuditSession.objects.create(
            tenant=self.tenant,
            property=self.property,
            audit_date=timezone.now().date(),
            total_room_charges_posted=Decimal("1200.00")
        )
        self.assertEqual(session.status, "PENDING")
