import random
import string
import logging
from abc import ABC, abstractmethod
from django.db import models
from django.utils import timezone
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from apps.core.accounts.models import AppUser
from apps.core.rbac.models import UserPropertyRole

from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# --- OTP PROVIDERS ---

class BaseOTPProvider(ABC):
    @abstractmethod
    def send_otp(self, contact: str, code: str) -> bool:
        """
        Sends the generated OTP code to the target contact (email or phone).
        Returns True if successful, False otherwise.
        """
        pass

class MockOTPProvider(BaseOTPProvider):
    def send_otp(self, contact: str, code: str) -> bool:
        logger.info(f"[MOCK OTP PROVIDER] Dispatching OTP code '{code}' to '{contact}'")
        print(f"\n--- [MOCK OTP] Code '{code}' dispatched to '{contact}' ---\n")
        return True

class EmailOTPProvider(BaseOTPProvider):
    def send_otp(self, contact: str, code: str) -> bool:
        logger.info(f"[EMAIL OTP PROVIDER] Dispatching Email OTP '{code}' to '{contact}'")
        try:
            from django.core.mail import EmailMultiAlternatives
            
            subject = 'Retrod PMS OTP Verification Code'
            text_content = f'Your Retrod PMS OTP verification code is: {code}. It is valid for 5 minutes.'
            
            # Premium HTML Template with dark modes, glassmorphism-like borders and custom fonts.
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Retrod PMS OTP Verification</title>
                <style>
                    body {{
                        font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                        background-color: #f8fafc;
                        color: #1e293b;
                        margin: 0;
                        padding: 0;
                        -webkit-font-smoothing: antialiased;
                    }}
                    .container {{
                        max-width: 520px;
                        margin: 40px auto;
                        background: #ffffff;
                        border-radius: 16px;
                        border: 1px solid #e2e8f0;
                        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #0f172a, #1e293b);
                        padding: 32px 24px;
                        text-align: center;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: 800;
                        color: #ffffff;
                        letter-spacing: -0.5px;
                        margin: 0;
                    }}
                    .logo span {{
                        color: #3b82f6;
                    }}
                    .body {{
                        padding: 40px 32px;
                    }}
                    .title {{
                        font-size: 20px;
                        font-weight: 700;
                        color: #0f172a;
                        margin-top: 0;
                        margin-bottom: 12px;
                        text-align: center;
                    }}
                    .intro {{
                        font-size: 14px;
                        line-height: 24px;
                        color: #475569;
                        text-align: center;
                        margin-bottom: 32px;
                    }}
                    .otp-box {{
                        background-color: #f1f5f9;
                        border-radius: 12px;
                        padding: 20px 24px;
                        text-align: center;
                        margin: 24px 0;
                        border: 1px dashed #cbd5e1;
                    }}
                    .otp-code {{
                        font-family: 'Courier New', Courier, monospace;
                        font-size: 32px;
                        font-weight: 800;
                        letter-spacing: 6px;
                        color: #2563eb;
                        margin: 0;
                    }}
                    .expiry-tag {{
                        font-size: 12px;
                        color: #64748b;
                        margin-top: 8px;
                        margin-bottom: 0;
                        font-weight: 500;
                    }}
                    .security-notice {{
                        font-size: 12px;
                        line-height: 18px;
                        color: #94a3b8;
                        text-align: center;
                        border-top: 1px solid #f1f5f9;
                        padding-top: 24px;
                        margin-top: 32px;
                    }}
                    .footer {{
                        background-color: #f8fafc;
                        padding: 20px;
                        text-align: center;
                        font-size: 11px;
                        color: #94a3b8;
                        border-top: 1px solid #e2e8f0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 class="logo">RETROD<span>PMS</span></h1>
                    </div>
                    <div class="body">
                        <h2 class="title">Verify Your Identity</h2>
                        <p class="intro">
                            You've requested to log in to Retrod PMS. Use the verification code below to complete your login sequence.
                        </p>
                        <div class="otp-box">
                            <h3 class="otp-code">{code}</h3>
                            <p class="expiry-tag">Valid for 5 minutes • Single use only</p>
                        </div>
                        <p class="security-notice">
                            If you did not initiate this request, you can safely ignore this email or reach out to platform security if you suspect unauthorized access.
                        </p>
                    </div>
                    <div class="footer">
                        &copy; 2026 Retrod Technologies Inc. All rights reserved.
                    </div>
                </div>
            </body>
            </html>
            """
            
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@retrod.io')
            email = EmailMultiAlternatives(subject, text_content, from_email, [contact])
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            return True
        except Exception as e:
            logger.error(f"Failed to send email OTP: {e}")
            return False


class SMSOTPProvider(BaseOTPProvider):
    def send_otp(self, contact: str, code: str) -> bool:
        logger.info(f"[SMS OTP PROVIDER] Dispatching SMS OTP '{code}' to '{contact}'")
        # In a real setup: twilio_client.messages.create(...)
        return True

# Provider Factory
def get_otp_provider(provider_type: str = 'mock') -> BaseOTPProvider:
    providers = {
        'mock': MockOTPProvider,
        'email': EmailOTPProvider,
        'sms': SMSOTPProvider
    }
    return providers.get(provider_type.lower(), MockOTPProvider)()


# --- AUTHENTICATION SERVICES ---

class AuthService:
    @staticmethod
    def get_tokens_for_user(user: AppUser):
        """
        Generates JWT access and refresh tokens for a user.
        """
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    @classmethod
    def create_user_session(cls, user: AppUser, tokens: dict, request=None):
        """
        Records the login session and maps token JTIs to tracking model.
        """
        if not request:
            return

        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        device = request.META.get('HTTP_USER_AGENT', 'Unknown')

        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        refresh_jti = None
        access_jti = None
        try:
            refresh_token = RefreshToken(tokens['refresh'])
            refresh_jti = refresh_token.get('jti')
            access_token = AccessToken(tokens['access'])
            access_jti = access_token.get('jti')
        except Exception:
            pass

        from apps.core.accounts.models import UserSession
        UserSession.objects.create(
            user=user,
            device=device,
            ip=ip,
            refresh_token_jti=refresh_jti,
            access_token_jti=access_jti,
            is_active=True
        )


    @staticmethod
    def check_user_lockout(user: AppUser) -> tuple[bool, str]:
        """
        Verifies if the user is currently locked out.
        """
        if user.lockout_expires_at and timezone.now() < user.lockout_expires_at:
            time_left = int((user.lockout_expires_at - timezone.now()).total_seconds() / 60)
            return True, f"Account is locked. Try again in {max(1, time_left)} minutes."
        
        # If lockout window has expired, reset failed attempts
        if user.lockout_expires_at and timezone.now() >= user.lockout_expires_at:
            user.failed_login_attempts = 0
            user.lockout_expires_at = None
            user.save(update_fields=['failed_login_attempts', 'lockout_expires_at'])
            
        return False, ""

    @staticmethod
    def handle_failed_login(user: AppUser, ip_address: str = "127.0.0.1"):
        """
        Increments failed login counter and triggers lockout if threshold reached.
        """
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.lockout_expires_at = timezone.now() + timezone.timedelta(minutes=15)
            from apps.core.accounts.models import AccountLock
            AccountLock.objects.update_or_create(
                user=user,
                defaults={
                    'locked_until': user.lockout_expires_at,
                    'reason': 'Locked due to 5 consecutive failed login attempts.'
                }
            )
            logger.warning(f"User {user.email} locked out due to consecutive failed attempts.")
        user.save(update_fields=['failed_login_attempts', 'lockout_expires_at'])

        # Record attempt
        from apps.core.accounts.models import LoginAttempt
        LoginAttempt.objects.create(
            user=user,
            ip_address=ip_address,
            success=False
        )

    @staticmethod
    def handle_successful_login(user: AppUser, ip_address: str = "127.0.0.1"):
        """
        Resets login tracking counters on success.
        """
        user.failed_login_attempts = 0
        user.lockout_expires_at = None
        user.last_login = timezone.now()
        user.save(update_fields=['failed_login_attempts', 'lockout_expires_at', 'last_login'])

        # Remove lock if exists
        from apps.core.accounts.models import AccountLock
        AccountLock.objects.filter(user=user).delete()

        # Record attempt
        from apps.core.accounts.models import LoginAttempt
        LoginAttempt.objects.create(
            user=user,
            ip_address=ip_address,
            success=True
        )

    @classmethod
    def authenticate_password(cls, tenant, email_or_username: str, password: str, ip_address: str = "127.0.0.1") -> tuple[AppUser | None, str]:
        """
        Authenticates a user using email or username + password in a tenant context.
        """
        try:
            # Query by email or username within the tenant
            user = AppUser.objects.get(
                models.Q(email__iexact=email_or_username) | models.Q(username__iexact=email_or_username),
                tenant=tenant,
                deleted_at__isnull=True
            )
        except AppUser.DoesNotExist:
            # Fallback: query globally if not found in the resolved tenant context (useful for localhost)
            try:
                user = AppUser.objects.get(
                    models.Q(email__iexact=email_or_username) | models.Q(username__iexact=email_or_username),
                    deleted_at__isnull=True
                )
            except AppUser.DoesNotExist:
                return None, "Invalid credentials."

        if not user.is_active:
            return None, "User account is deactivated."

        # Lockout check
        is_locked, msg = cls.check_user_lockout(user)
        if is_locked:
            return None, msg

        # Verify password
        if not user.check_password(password):
            cls.handle_failed_login(user, ip_address)
            # Recheck if user got locked out right now
            is_locked, msg = cls.check_user_lockout(user)
            if is_locked:
                return None, msg
            return None, "Invalid credentials."

        cls.handle_successful_login(user, ip_address)
        return user, "Success"

    @classmethod
    def request_otp(cls, tenant, contact: str, provider_type: str = 'mock') -> tuple[bool, str]:
        """
        Generates and sends an OTP to user phone or email.
        """
        try:
            user = AppUser.objects.get(
                models.Q(email__iexact=contact) | models.Q(phone=contact),
                tenant=tenant,
                deleted_at__isnull=True
            )
        except AppUser.DoesNotExist:
            try:
                user = AppUser.objects.get(
                    models.Q(email__iexact=contact) | models.Q(phone=contact),
                    deleted_at__isnull=True
                )
            except AppUser.DoesNotExist:
                return False, "User not found."

        if not user.is_active:
            return False, "User account is deactivated."

        is_locked, msg = cls.check_user_lockout(user)
        if is_locked:
            return False, msg

        # Generate 6-digit numeric OTP code
        code = "".join(random.choices(string.digits, k=6))
        user.otp_code = code
        user.otp_expires_at = timezone.now() + timezone.timedelta(minutes=5)
        user.save(update_fields=['otp_code', 'otp_expires_at'])

        # Dispatch code
        provider = get_otp_provider(provider_type)
        dispatched = provider.send_otp(contact, code)
        
        if not dispatched:
            return False, "Failed to send OTP code. Try again."

        return True, "OTP code sent successfully."

    @classmethod
    def verify_otp(cls, tenant, contact: str, otp_code: str, ip_address: str = "127.0.0.1") -> tuple[AppUser | None, str]:
        """
        Validates OTP code and logs the user in on success.
        """
        try:
            user = AppUser.objects.get(
                models.Q(email__iexact=contact) | models.Q(phone=contact),
                tenant=tenant,
                deleted_at__isnull=True
            )
        except AppUser.DoesNotExist:
            try:
                user = AppUser.objects.get(
                    models.Q(email__iexact=contact) | models.Q(phone=contact),
                    deleted_at__isnull=True
                )
            except AppUser.DoesNotExist:
                return None, "Invalid request."

        # Lockout check
        is_locked, msg = cls.check_user_lockout(user)
        if is_locked:
            return None, msg

        # Check expiry
        if not user.otp_expires_at or timezone.now() > user.otp_expires_at:
            return None, "OTP code has expired."

        # Check code
        if user.otp_code != otp_code:
            cls.handle_failed_login(user, ip_address)
            # Recheck lockout
            is_locked, msg = cls.check_user_lockout(user)
            if is_locked:
                return None, msg
            return None, "Invalid OTP code."

        # Clear OTP fields on success
        user.otp_code = None
        user.otp_expires_at = None
        user.save(update_fields=['otp_code', 'otp_expires_at'])
        
        cls.handle_successful_login(user, ip_address)
        return user, "Success"

    @staticmethod
    def get_user_metadata(user: AppUser, tenant):
        """
        Returns serialized metadata required by the frontend layout:
        User details, roles/permissions list, and authorized properties.
        """
        # Resolve properties and roles mapped to user
        property_roles = UserPropertyRole.objects.filter(user=user, tenant=tenant)
        properties = []
        permissions = set()
        
        for pr in property_roles:
            properties.append({
                'id': str(pr.property.id),
                'name': pr.property.name,
                'role': pr.role.code
            })
            # Add role permissions
            for rp in pr.role.permissions.all():
                permissions.add(rp.permission.code)

        # Resolve tenant-wide assignment role and permissions (e.g. for owner onboarding)
        from apps.core.accounts.models import UserAssignment
        assignment = UserAssignment.objects.filter(user=user, tenant=tenant).first()
        user_role = assignment.role.code if (assignment and assignment.role) else None

        if assignment and assignment.role:
            for rp in assignment.role.permissions.all():
                permissions.add(rp.permission.code)

        # Include superuser properties bypass if relevant
        if user.is_superuser:
            user_role = 'super_admin'
            permissions.add("*:*")  # Wildcard system permission
            from apps.core.tenants.models import Property
            for p in Property.objects.filter(tenant=tenant):
                properties.append({
                    'id': str(p.id),
                    'name': p.name,
                    'role': 'super_admin'
                })

        # Fetch subscription plan details
        from apps.core.subscriptions.models import TenantSubscription, TenantProductLicense
        sub = TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').first()
        sub_plan = sub.plan.name if sub else "Standard Enterprise Plan"
        sub_expiry = str(sub.end_date) if sub else "2027-01-31"
        
        # Fetch license key
        lic = TenantProductLicense.objects.filter(tenant_product__tenant=tenant, tenant_product__product__code='PMS', status='ACTIVE').first()
        if not lic:
            lic = TenantProductLicense.objects.filter(tenant_product__tenant=tenant, status='ACTIVE').first()
        license_key = lic.license_key if lic else "RETROD-LNX-8394-2026"

        return {
            'user': {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'username': user.username,
                'phone': user.phone,
                'avatar_url': user.avatar_url,
                'preferred_language': user.preferred_language,
                'preferred_timezone': user.preferred_timezone,
                'role': user_role,
                'tenant_subdomain': user.tenant.subdomain if user.tenant else None,
                'subscription_plan': sub_plan,
                'subscription_expiry': sub_expiry,
                'license_key': license_key,
            },
            'permissions': list(permissions),
            'properties': properties
        }
