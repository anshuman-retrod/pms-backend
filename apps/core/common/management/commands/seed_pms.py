from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.tenants.models import Tenant, Property
from apps.core.rbac.models import Permission, Role, RolePermission, UserPropertyRole

class Command(BaseCommand):
    help = 'Bootstrap Retrod PMS database with default roles, permissions, tenants, properties, and staff accounts.'

    def handle(self, *args, **options):
        self.stdout.write("Bootstrapping Retrod PMS Database...")

        # 1. Create Tenants
        tenant_gp, _ = Tenant.objects.get_or_create(
            subdomain='grandpalace',
            defaults={
                'name': 'The Grand Palace Group',
                'status': 'active',
                'country': 'India',
                'currency': 'INR',
                'timezone': 'Asia/Kolkata'
            }
        )
        tenant_demo, _ = Tenant.objects.get_or_create(
            subdomain='demo',
            defaults={
                'name': 'Retrod Demo Hotel',
                'status': 'active',
                'country': 'India',
                'currency': 'INR',
                'timezone': 'Asia/Kolkata'
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Created tenants: {tenant_gp}, {tenant_demo}"))

        # 2. Create Properties
        prop_delhi, _ = Property.objects.get_or_create(
            tenant=tenant_gp,
            name='The Grand Palace - New Delhi',
            defaults={
                'property_type': 'HOTEL',
                'address_line_1': '1 Parliament Street',
                'city': 'New Delhi',
                'state': 'Delhi',
                'country': 'India',
                'postal_code': '110001',
                'contact_email': 'delhi@grandpalace.in',
                'contact_phone': '+91 11 4123 4567',
                'currency': 'INR',
                'timezone': 'Asia/Kolkata',
                'is_active': True
            }
        )
        prop_goa, _ = Property.objects.get_or_create(
            tenant=tenant_gp,
            name='The Grand Palace Resort - Goa',
            defaults={
                'property_type': 'VILLA',
                'address_line_1': 'Candolim Beach Road',
                'city': 'Goa',
                'state': 'Goa',
                'country': 'India',
                'postal_code': '403515',
                'contact_email': 'goa@grandpalace.in',
                'contact_phone': '+91 832 245 6789',
                'currency': 'INR',
                'timezone': 'Asia/Kolkata',
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS(f"Created properties: {prop_delhi}, {prop_goa}"))

        # 3. Create Permissions Catalog
        permission_list = [
            # Reservation
            ('reservation.create', 'reservation'),
            ('reservation.view', 'reservation'),
            ('reservation.edit', 'reservation'),
            ('reservation.cancel', 'reservation'),
            # Billing
            ('billing.view', 'billing'),
            ('billing.edit', 'billing'),
            ('billing.void', 'billing'),
            ('billing.refund', 'billing'),
            # Housekeeping
            ('housekeeping.view', 'housekeeping'),
            ('housekeeping.edit', 'housekeeping'),
            # Rates
            ('rates.view', 'rates'),
            ('rates.edit', 'rates'),
            # Administration
            ('settings.view', 'settings'),
            ('settings.edit', 'settings'),
        ]

        perms = {}
        for code, category in permission_list:
            perm, _ = Permission.objects.get_or_create(code=code, defaults={'category': category})
            perms[code] = perm

        self.stdout.write(self.style.SUCCESS(f"Populated {len(perms)} default system permissions."))

        # 4. Create Tenant-specific Roles
        roles_data = [
            ('super_admin', 'Super Admin', 'Full master developer control'),
            ('owner', 'Owner', 'Full property group management'),
            ('general_manager', 'General Manager', 'Full property local operations management'),
            ('front_office_manager', 'Front Office Manager', 'Front desk oversight and checklists'),
            ('front_desk_agent', 'Front Desk Agent', 'Front office checkin/checkout transactions'),
            ('housekeeping_supervisor', 'Housekeeping Supervisor', 'Room status coordination'),
            ('accounts', 'Accounts', 'Invoices and balance settlement processing'),
            ('revenue_manager', 'Revenue Manager', 'Yield optimization configurations'),
        ]

        roles = {}
        for r_code, r_name, r_desc in roles_data:
            role, _ = Role.objects.get_or_create(
                tenant=tenant_gp,
                code=r_code,
                defaults={'name': r_name, 'description': r_desc}
            )
            roles[r_code] = role

        self.stdout.write(self.style.SUCCESS(f"Populated {len(roles)} default staff roles."))

        # 5. Link Permissions to Roles
        role_permission_mappings = {
            'owner': ['reservation.create', 'reservation.view', 'reservation.edit', 'reservation.cancel', 'billing.view', 'billing.edit', 'billing.void', 'billing.refund', 'housekeeping.view', 'housekeeping.edit', 'rates.view', 'rates.edit', 'settings.view', 'settings.edit'],
            'general_manager': ['reservation.create', 'reservation.view', 'reservation.edit', 'reservation.cancel', 'billing.view', 'billing.edit', 'housekeeping.view', 'housekeeping.edit', 'rates.view', 'rates.edit', 'settings.view'],
            'front_office_manager': ['reservation.create', 'reservation.view', 'reservation.edit', 'reservation.cancel', 'billing.view', 'billing.edit', 'housekeeping.view', 'housekeeping.edit', 'rates.view'],
            'front_desk_agent': ['reservation.create', 'reservation.view', 'reservation.edit', 'housekeeping.view'],
            'housekeeping_supervisor': ['housekeeping.view', 'housekeeping.edit'],
            'accounts': ['billing.view', 'billing.edit', 'billing.void', 'billing.refund'],
            'revenue_manager': ['rates.view', 'rates.edit', 'reservation.view'],
        }

        for r_code, perm_codes in role_permission_mappings.items():
            role = roles.get(r_code)
            if role:
                for p_code in perm_codes:
                    perm = perms.get(p_code)
                    if perm:
                        RolePermission.objects.get_or_create(role=role, permission=perm)

        self.stdout.write(self.style.SUCCESS("Wired up default role-permission mappings."))

        # 6. Create Users & Property Roles
        User = get_user_model()
        users_data = [
            ('aarav@grandpalace.in', 'Aarav Malhotra', 'aarav', 'owner', prop_delhi),
            ('vikram@grandpalace.in', 'Vikram Shah', 'vikram', 'general_manager', prop_delhi),
            ('neha@grandpalace.in', 'Neha Kapoor', 'neha', 'front_office_manager', prop_delhi),
            ('rohan@grandpalace.in', 'Rohan Verma', 'rohan', 'front_desk_agent', prop_delhi),
        ]

        for email, name, username, r_code, prop in users_data:
            user, created = User.objects.get_or_create(
                tenant=tenant_gp,
                email=email,
                defaults={
                    'name': name,
                    'username': username,
                    'phone': '+91 99999 88888',
                    'preferred_language': 'en',
                    'preferred_timezone': 'Asia/Kolkata',
                    'is_active': True
                }
            )
            if created:
                user.set_password('Password123')
                user.save()

            role = roles.get(r_code)
            if role:
                UserPropertyRole.objects.get_or_create(
                    tenant=tenant_gp,
                    user=user,
                    property=prop,
                    role=role
                )
            
            # Map vikram (GM) to Goa property as well
            if username == 'vikram':
                UserPropertyRole.objects.get_or_create(
                    tenant=tenant_gp,
                    user=user,
                    property=prop_goa,
                    role=role
                )

        # Create global Superuser
        superuser_email = 'admin@retrod.in'
        if not User.objects.filter(email=superuser_email).exists():
            User.objects.create_superuser(
                email=superuser_email,
                password='Password123',
                name='Retrod System Admin',
                username='sysadmin'
            )
            self.stdout.write(self.style.SUCCESS("Created master superuser: admin@retrod.in"))

        # Create user anshumanbiswal549@gmail.com as superuser under tenant_gp
        anshu_email = 'anshumanbiswal549@gmail.com'
        if not User.objects.filter(email=anshu_email).exists():
            user = User.objects.create_superuser(
                email=anshu_email,
                password='Password123',
                name='Anshuman Biswal',
                username='anshuman',
                tenant=tenant_gp
            )
            self.stdout.write(self.style.SUCCESS("Created superuser under tenant_gp: anshumanbiswal549@gmail.com"))
            
            # Link to prop_delhi with super_admin role
            role = roles.get('super_admin')
            if role:
                UserPropertyRole.objects.get_or_create(
                    tenant=tenant_gp,
                    user=user,
                    property=prop_delhi,
                    role=role
                )

        # Seed default languages, taxes, docs, facilities, currencies, and formats
        from apps.core.common.models import (
            SystemLanguage, SystemTax, SystemDocumentType,
            SystemFacility, SystemCurrency, SystemDateFormat, SystemTimeFormat
        )
        
        SystemLanguage.objects.get_or_create(code='en', defaults={'name': 'English', 'is_active': True, 'is_default': True})
        SystemLanguage.objects.get_or_create(code='hi', defaults={'name': 'Hindi', 'is_active': True, 'is_default': False})
        SystemLanguage.objects.get_or_create(code='fr', defaults={'name': 'French', 'is_active': False, 'is_default': False})

        # Seed Taxes
        SystemTax.objects.get_or_create(name="VAT (Value Added Tax)", defaults={'rate': 15.00, 'type': 'percentage', 'status': 'active', 'tenant': None})
        SystemTax.objects.get_or_create(name="Service Tax", defaults={'rate': 5.00, 'type': 'percentage', 'status': 'active', 'tenant': None})
        SystemTax.objects.get_or_create(name="Tourism Levy", defaults={'rate': 10.00, 'type': 'fixed', 'status': 'inactive', 'tenant': None})

        # Seed Document Types
        SystemDocumentType.objects.get_or_create(name="Passport", defaults={'required_checkin': True, 'expiry_required': True, 'tenant': None})
        SystemDocumentType.objects.get_or_create(name="National ID Card", defaults={'required_checkin': True, 'expiry_required': False, 'tenant': None})
        SystemDocumentType.objects.get_or_create(name="Driver's License", defaults={'required_checkin': False, 'expiry_required': True, 'tenant': None})

        # Seed Facilities
        SystemFacility.objects.get_or_create(name="High-Speed Wi-Fi", defaults={'chargeable': False, 'price': 0.00, 'description': 'Complimentary gigabit fiber connection in all rooms and public areas.', 'icon_name': 'wifi', 'tenant': None})
        SystemFacility.objects.get_or_create(name="Swimming Pool", defaults={'chargeable': False, 'price': 0.00, 'description': 'Access to outdoor heated infinity swimming pool.', 'icon_name': 'pool', 'tenant': None})
        SystemFacility.objects.get_or_create(name="Spa", defaults={'chargeable': True, 'price': 50.00, 'description': 'Full-service wellness treatments, massage therapy, and sauna.', 'icon_name': 'spa', 'tenant': None})

        # Seed Currencies
        SystemCurrency.objects.get_or_create(code="USD", defaults={'symbol': '$', 'name': 'US Dollar', 'is_active': True, 'is_default': True, 'tenant': None})
        SystemCurrency.objects.get_or_create(code="INR", defaults={'symbol': '₹', 'name': 'Indian Rupee', 'is_active': True, 'is_default': False, 'tenant': None})
        SystemCurrency.objects.get_or_create(code="EUR", defaults={'symbol': '€', 'name': 'Euro', 'is_active': True, 'is_default': False, 'tenant': None})

        # Seed Date Formats
        SystemDateFormat.objects.get_or_create(format="YYYY-MM-DD", defaults={'label': '2026-06-27', 'is_default': True, 'tenant': None})
        SystemDateFormat.objects.get_or_create(format="DD/MM/YYYY", defaults={'label': '27/06/2026', 'is_default': False, 'tenant': None})

        # Seed Time Formats
        SystemTimeFormat.objects.get_or_create(format="HH:mm", defaults={'label': '14:30', 'is_default': True, 'tenant': None})
        SystemTimeFormat.objects.get_or_create(format="hh:mm A", defaults={'label': '02:30 PM', 'is_default': False, 'tenant': None})

        self.stdout.write(self.style.SUCCESS("Retrod PMS Database successfully bootstrapped!"))
