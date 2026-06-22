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
            send_mail(
                subject='Retrod PMS OTP Verification Code',
                message=f'Your Retrod PMS OTP verification code is: {code}. It is valid for 5 minutes.',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@retrod.io'),
                recipient_list=[contact],
                fail_silently=False,
            )
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
    def handle_failed_login(user: AppUser):
        """
        Increments failed login counter and triggers lockout if threshold reached.
        """
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.lockout_expires_at = timezone.now() + timezone.timedelta(minutes=15)
            logger.warning(f"User {user.email} locked out due to consecutive failed attempts.")
        user.save(update_fields=['failed_login_attempts', 'lockout_expires_at'])

    @staticmethod
    def handle_successful_login(user: AppUser):
        """
        Resets login tracking counters on success.
        """
        user.failed_login_attempts = 0
        user.lockout_expires_at = None
        user.last_login = timezone.now()
        user.save(update_fields=['failed_login_attempts', 'lockout_expires_at', 'last_login'])

    @classmethod
    def authenticate_password(cls, tenant, email_or_username: str, password: str) -> tuple[AppUser | None, str]:
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
            return None, "Invalid credentials."

        if not user.is_active:
            return None, "User account is deactivated."

        # Lockout check
        is_locked, msg = cls.check_user_lockout(user)
        if is_locked:
            return None, msg

        # Verify password
        if not user.check_password(password):
            cls.handle_failed_login(user)
            # Recheck if user got locked out right now
            is_locked, msg = cls.check_user_lockout(user)
            if is_locked:
                return None, msg
            return None, "Invalid credentials."

        cls.handle_successful_login(user)
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
    def verify_otp(cls, tenant, contact: str, otp_code: str) -> tuple[AppUser | None, str]:
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
            cls.handle_failed_login(user)
            # Recheck lockout
            is_locked, msg = cls.check_user_lockout(user)
            if is_locked:
                return None, msg
            return None, "Invalid OTP code."

        # Clear OTP fields on success
        user.otp_code = None
        user.otp_expires_at = None
        user.save(update_fields=['otp_code', 'otp_expires_at'])
        
        cls.handle_successful_login(user)
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

        # Include superuser properties bypass if relevant
        if user.is_superuser:
            permissions.add("*:*")  # Wildcard system permission
            from apps.core.tenants.models import Property
            for p in Property.objects.filter(tenant=tenant):
                properties.append({
                    'id': str(p.id),
                    'name': p.name,
                    'role': 'super_admin'
                })

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
            },
            'permissions': list(permissions),
            'properties': properties
        }
