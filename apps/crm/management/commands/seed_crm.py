from django.core.management.base import BaseCommand
from datetime import date
from decimal import Decimal
from apps.tenants.models import Tenant
from apps.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)
from apps.crm.services import EncryptionHelper

class Command(BaseCommand):
    help = 'Seed Guest Tags, Guest Profiles, primary Contacts, Preferences, Documents and timeline events.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Guest CRM Domain...")

        # 1. Fetch Tenant
        tenant_gp = Tenant.objects.filter(subdomain='grandpalace').first()
        if not tenant_gp:
            self.stdout.write(self.style.ERROR("Tenant 'grandpalace' not found. Run seed_pms first!"))
            return

        # 2. Seed Default Guest Tags
        tags = {}
        tag_data = [
            ('VIP', 'Very Important Person'),
            ('REPEAT_GUEST', 'Repeat Visitor'),
            ('CORP_BOOKER', 'Corporate Booker'),
            ('BLACKLIST', 'Blacklisted Guest'),
        ]
        for code, name in tag_data:
            tag, created = GuestTag.objects.get_or_create(
                tenant=tenant_gp,
                code=code,
                defaults={'name': name}
            )
            tags[code] = tag
            if created:
                self.stdout.write(f"Created guest tag: {code}")

        # 3. Seed Guest Profiles
        # Profile 1: John Doe
        john, created = GuestProfile.objects.get_or_create(
            tenant=tenant_gp,
            first_name='John',
            last_name='Doe',
            defaults={
                'date_of_birth': date(1985, 4, 12),
                'gender': 'MALE',
                'nationality': 'American',
                'guest_type': 'VIP',
                'loyalty_tier': 'GOLD',
                'loyalty_points': 6500,
                'nps_score': 9,
                'vip_notes': 'Prefers high floor and extra towels.',
                'email_opt_in': True,
                'sms_opt_in': False,
                'whatsapp_opt_in': True,
                'total_stays': 5,
                'total_nights': 12,
                'last_stay_date': date(2026, 5, 20),
                'is_active': True
            }
        )
        if created:
            self.stdout.write("Created Guest Profile: John Doe")
            # Create contact
            GuestContact.objects.create(
                tenant=tenant_gp,
                guest=john,
                email='john.doe@vip-guest.com',
                phone='+12025550143',
                city='New York',
                country='USA',
                is_primary=True
            )
            # Create document
            GuestDocument.objects.create(
                tenant=tenant_gp,
                guest=john,
                document_type='PASSPORT',
                document_number=EncryptionHelper.encrypt('US123456789'),
                expiry_date=date(2032, 10, 1),
                issuing_country='USA',
                is_verified=True
            )
            # Create preferences
            GuestPreference.objects.create(
                tenant=tenant_gp,
                guest=john,
                preference_category='ROOM',
                preference_key='floor_pref',
                preference_value='High-Floor'
            )
            GuestPreference.objects.create(
                tenant=tenant_gp,
                guest=john,
                preference_category='DIETARY',
                preference_key='allergies',
                preference_value='Peanuts'
            )
            # Assign Tag
            GuestProfileTag.objects.create(guest=john, tag=tags['VIP'])
            # Activities
            GuestActivity.objects.create(
                tenant=tenant_gp,
                guest=john,
                activity_type='PROFILE_CREATED',
                description='Guest profile initialized in CRM.'
            )
            GuestActivity.objects.create(
                tenant=tenant_gp,
                guest=john,
                activity_type='STAY_COMPLETED',
                description='Stay completed at Delhi Palace. Delhi Room 301, 3 nights.'
            )

        # Profile 2: Jane Smith
        jane, created = GuestProfile.objects.get_or_create(
            tenant=tenant_gp,
            first_name='Jane',
            last_name='Smith',
            defaults={
                'date_of_birth': date(1991, 8, 24),
                'gender': 'FEMALE',
                'nationality': 'British',
                'guest_type': 'DOMESTIC',
                'loyalty_tier': 'STANDARD',
                'loyalty_points': 300,
                'nps_score': 10,
                'email_opt_in': True,
                'sms_opt_in': True,
                'total_stays': 1,
                'total_nights': 2,
                'last_stay_date': date(2026, 6, 1),
                'is_active': True
            }
        )
        if created:
            self.stdout.write("Created Guest Profile: Jane Smith")
            GuestContact.objects.create(
                tenant=tenant_gp,
                guest=jane,
                email='jane.smith@gmail.com',
                phone='+447911123456',
                city='London',
                country='UK',
                is_primary=True
            )
            GuestDocument.objects.create(
                tenant=tenant_gp,
                guest=jane,
                document_type='NATIONAL_ID',
                document_number=EncryptionHelper.encrypt('GB987654321A'),
                expiry_date=date(2029, 12, 31),
                issuing_country='UK',
                is_verified=False
            )
            GuestActivity.objects.create(
                tenant=tenant_gp,
                guest=jane,
                activity_type='PROFILE_CREATED',
                description='Guest profile initialized in CRM.'
            )

        self.stdout.write(self.style.SUCCESS("CRM database successfully seeded!"))
