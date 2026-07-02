from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.core.tenants.models import Tenant, Property
from apps.features.crm.models import GuestProfile
from apps.core.reference.models import Country, ReservationSource
from apps.features.reservations.models import Reservation
from apps.features.front_office.models import GuestFolio
from apps.features.billing.models import TaxRate, Invoice, InvoiceLineItem, CreditNote, BillingAdjustment

class BillingModelsTestCase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Hotel Biraj Group", subdomain="biraj")
        self.property = Property.objects.create(tenant=self.tenant, name="Main Wing")
        
        self.guest = GuestProfile.objects.create(
            tenant=self.tenant,
            first_name="Aarav",
            last_name="Sharma"
        )
        self.source = ReservationSource.objects.create(code="DIRECT", name="Direct")
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
        self.folio = GuestFolio.objects.create(
            tenant=self.tenant,
            reservation=self.reservation,
            folio_number="FOLIO9901"
        )

    def test_tax_rate_creation(self):
        tax = TaxRate.objects.create(
            tenant=self.tenant,
            name="GST 18%",
            code="GST18",
            percentage=Decimal("18.00")
        )
        self.assertEqual(tax.code, "GST18")
        self.assertTrue(tax.is_active)

    def test_invoice_creation(self):
        inv = Invoice.objects.create(
            tenant=self.tenant,
            folio=self.folio,
            invoice_number="INV7701",
            invoice_type="TAX_INVOICE",
            total_amount=Decimal("500.00"),
            tax_amount=Decimal("90.00"),
            net_amount=Decimal("590.00")
        )
        self.assertEqual(inv.invoice_number, "INV7701")
        self.assertEqual(inv.invoice_type, "TAX_INVOICE")

    def test_invoice_line_item(self):
        inv = Invoice.objects.create(
            tenant=self.tenant,
            folio=self.folio,
            invoice_number="INV7702",
            total_amount=Decimal("150.00"),
            net_amount=Decimal("150.00")
        )
        line = InvoiceLineItem.objects.create(
            invoice=inv,
            description="Room Night Charge",
            quantity=1,
            unit_price=Decimal("150.00"),
            net_amount=Decimal("150.00")
        )
        self.assertEqual(line.quantity, 1)

    def test_credit_note_creation(self):
        inv = Invoice.objects.create(
            tenant=self.tenant,
            folio=self.folio,
            invoice_number="INV7703"
        )
        cn = CreditNote.objects.create(
            tenant=self.tenant,
            original_invoice=inv,
            credit_note_number="CN5501",
            credit_amount=Decimal("50.00"),
            reason="Room downgrade adjustment"
        )
        self.assertEqual(cn.credit_note_number, "CN5501")

    def test_billing_adjustment_creation(self):
        adj = BillingAdjustment.objects.create(
            tenant=self.tenant,
            folio=self.folio,
            adjustment_type="DISCOUNT",
            amount=Decimal("25.00"),
            reason="Loyal guest discount"
        )
        self.assertFalse(adj.is_approved)
        self.assertEqual(adj.amount, Decimal("25.00"))
