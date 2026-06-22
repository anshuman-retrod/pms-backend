from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.core.tenants.models import Tenant, Property
from apps.features.crm.models import GuestProfile, GuestContact
from apps.core.reference.models import Country, ReservationSource
from apps.features.inventory.models import InventoryUnit, InventoryUnitType
from apps.features.rates.models import RatePlan, RatePlanVersion
from apps.features.reservations.models import CorporateAccount, GroupBlock
from apps.features.reservations.services import BookingEngine

class Command(BaseCommand):
    help = 'Seeds Reservation Domain data including Corporate Accounts, Group Blocks, and Reservations.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding reservations data...")

        # 1. Resolve Tenant & Property
        tenant = Tenant.objects.filter(status='active').first()
        if not tenant:
            self.stdout.write(self.style.ERROR("No active tenant found to seed reservations."))
            return
        
        property_obj = Property.objects.filter(tenant=tenant).first()
        if not property_obj:
            self.stdout.write(self.style.ERROR("No property found for tenant."))
            return

        # 2. Get standard references
        res_source_direct = ReservationSource.objects.filter(code='direct').first()
        res_source_booking = ReservationSource.objects.filter(code='booking_com').first()
        us_country = Country.objects.filter(code='US').first()

        if not res_source_direct or not res_source_booking:
            self.stdout.write(self.style.WARNING("Reservation sources not seeded. Please run seed_reference_data first."))
            return

        # 3. Create or Get Guest Profile
        guest, created = GuestProfile.objects.get_or_create(
            tenant=tenant,
            first_name="John",
            last_name="Doe",
            defaults={
                "preferred_language": "en",
                "guest_type": "DOMESTIC",
                "loyalty_tier": "STANDARD",
                "loyalty_points": 100,
                "is_active": True
            }
        )
        if created:
            GuestContact.objects.get_or_create(
                tenant=tenant,
                guest=guest,
                email="john.doe@seed.com",
                phone="+15550199",
                is_primary=True
            )

        # 4. Resolve Inventory Unit Type & Rate Plan
        unit_type = InventoryUnitType.objects.filter(property=property_obj, tenant=tenant).first()
        rate_plan = RatePlan.objects.filter(property=property_obj, tenant=tenant).first()
        if not unit_type or not rate_plan:
            self.stdout.write(self.style.WARNING("Inventory types or rate plans missing. Run seed_pms or configure inventory first."))
            return
        
        rate_version = RatePlanVersion.objects.filter(rate_plan=rate_plan).first()
        if not rate_version:
            # Create a mock version
            rate_version = RatePlanVersion.objects.create(
                rate_plan=rate_plan,
                version_number=1,
                snapshot={},
                effective_from=timezone.now()
            )

        # 5. Create Corporate Account
        corp_account, _ = CorporateAccount.objects.get_or_create(
            tenant=tenant,
            company_name="Acme Corp",
            defaults={
                "negotiated_rate_code": "CORP_ACME",
                "credit_limit": Decimal("5000.00"),
                "is_active": True
            }
        )

        # 6. Create Group Block
        group_block, _ = GroupBlock.objects.get_or_create(
            tenant=tenant,
            property=property_obj,
            name="Alpha Wedding Block",
            defaults={
                "block_type": "Wedding Block",
                "cutoff_date": timezone.now().date() + timezone.timedelta(days=30),
                "status": "OPEN",
                "total_rooms": 10,
                "contracted_revenue": Decimal("2500.00")
            }
        )

        # 7. Seed Direct Reservation via Booking Engine
        booking_date = timezone.now().date()
        arrival_date = booking_date + timezone.timedelta(days=1)
        departure_date = booking_date + timezone.timedelta(days=3)

        booking_data = {
            'primary_guest_id': guest.id,
            'reservation_source_id': res_source_direct.id,
            'reservation_type': 'Guaranteed',
            'market_segment': 'Leisure',
            'origin_country_id': us_country.id if us_country else None,
            'arrival_date': arrival_date,
            'departure_date': departure_date,
            'booking_reference': 'DIR-12345',
            'notes': 'Seed booking notes',
            'remarks': 'Seed booking remarks',
            'special_requests': 'High floor please',
            'allocations': [
                {
                    'inventory_unit_type_id': unit_type.id,
                    'check_in_date': arrival_date,
                    'check_out_date': departure_date,
                    'adult_count': 2,
                    'child_count': 0,
                    'infant_count': 0,
                    'rate_plan_id': rate_plan.id,
                    'nightly_rates': [
                        {
                            'date': arrival_date,
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': rate_version.id
                        },
                        {
                            'date': arrival_date + timezone.timedelta(days=1),
                            'amount': Decimal('150.00'),
                            'rate_plan_version_id': rate_version.id
                        }
                    ]
                }
            ]
        }

        res = BookingEngine.create_booking(tenant, property_obj, booking_data)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded reservation: {res.confirmation_number}"))

        # 8. Seed Corporate Booking
        booking_data_corp = booking_data.copy()
        booking_data_corp['corporate_account_id'] = corp_account.id
        booking_data_corp['booking_reference'] = 'CORP-ACME-999'
        booking_data_corp['market_segment'] = 'Corporate'
        
        res_corp = BookingEngine.create_booking(tenant, property_obj, booking_data_corp)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded corporate reservation: {res_corp.confirmation_number}"))

        # 9. Seed Group Booking
        booking_data_group = booking_data.copy()
        booking_data_group['group_block_id'] = group_block.id
        booking_data_group['booking_reference'] = 'GRP-WED-001'
        booking_data_group['market_segment'] = 'Group'
        
        res_group = BookingEngine.create_booking(tenant, property_obj, booking_data_group)
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded group reservation: {res_group.confirmation_number}"))

        self.stdout.write(self.style.SUCCESS("Reservation seeding completed successfully!"))
