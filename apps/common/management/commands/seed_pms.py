from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant, Property
from apps.rbac.models import Permission, Role, RolePermission, UserPropertyRole

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

        self.stdout.write(self.style.SUCCESS("Retrod PMS Database successfully bootstrapped!"))
