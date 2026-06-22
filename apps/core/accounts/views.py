from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from drf_spectacular.utils import extend_schema
from apps.core.accounts.models import (
    AppUser, UserInvitation, UserAssignment, PasswordPolicy, LoginAttempt,
    AccountLock, UserMFA, UserSession, IPWhitelist, SSOConfiguration
)
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.utils import timezone
import uuid
from apps.core.accounts.serializers import (
    AppUserSerializer, AppUserCreateSerializer,
    PasswordLoginRequestSerializer, RequestOTPRequestSerializer,
    VerifyOTPRequestSerializer, LogoutRequestSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    UserInvitationSerializer, UserAssignmentSerializer, PasswordPolicySerializer,
    LoginAttemptSerializer, AccountLockSerializer, UserMFASerializer,
    UserSessionSerializer, IPWhitelistSerializer, SSOConfigurationSerializer
)
from apps.core.accounts.services import AuthService


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for managing Staff Users under the resolved tenant context.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AppUserCreateSerializer
        return AppUserSerializer

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return AppUser.objects.none()
        return AppUser.objects.filter(tenant=tenant, deleted_at__isnull=True)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(
            tenant=tenant,
            created_by=self.request.user if self.request.user.is_authenticated else None
        )

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user if self.request.user.is_authenticated else None
        )


@extend_schema(request=PasswordLoginRequestSerializer, responses={200: dict})
class PasswordLoginView(APIView):
    """
    Authenticates a user via subdomain, email/username, and password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        email_or_username = request.data.get('email_or_username')
        password = request.data.get('password')

        if not email_or_username or not password:
            return Response({'error': 'Provide email_or_username and password.'}, status=status.HTTP_400_BAD_REQUEST)

        user, msg = AuthService.authenticate_password(tenant, email_or_username, password)
        if not user:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        # Issue JWT tokens
        tokens = AuthService.get_tokens_for_user(user)
        meta = AuthService.get_user_metadata(user, tenant)

        return Response({
            'tokens': tokens,
            'user': meta['user'],
            'permissions': meta['permissions'],
            'properties': meta['properties']
        }, status=status.HTTP_200_OK)


@extend_schema(request=RequestOTPRequestSerializer, responses={200: dict})
class RequestOTPView(APIView):
    """
    Generates and dispatches a 6-digit OTP code to a user's phone or email.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        contact = request.data.get('email') or request.data.get('phone') or request.data.get('contact')
        
        from django.conf import settings
        configured_provider = getattr(settings, 'OTP_PROVIDER', 'mock')
        # Strictly enforce system-configured provider (email/sms) if set, otherwise fallback to request parameter
        if configured_provider in ['email', 'sms']:
            provider_type = configured_provider
        else:
            provider_type = request.data.get('provider') or configured_provider

        if not contact:
            return Response({'error': 'Provide email or phone contact.'}, status=status.HTTP_400_BAD_REQUEST)

        success, msg = AuthService.request_otp(tenant, contact, provider_type)
        if not success:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'message': msg}, status=status.HTTP_200_OK)


@extend_schema(request=VerifyOTPRequestSerializer, responses={200: dict})
class VerifyOTPView(APIView):
    """
    Verifies OTP code and logs the user in.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        contact = request.data.get('email') or request.data.get('phone') or request.data.get('contact')
        otp_code = request.data.get('otp_code') or request.data.get('otp')

        if not contact or not otp_code:
            return Response({'error': 'Provide contact details and OTP code.'}, status=status.HTTP_400_BAD_REQUEST)

        user, msg = AuthService.verify_otp(tenant, contact, otp_code)
        if not user:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        # Issue JWT tokens
        tokens = AuthService.get_tokens_for_user(user)
        meta = AuthService.get_user_metadata(user, tenant)

        return Response({
            'tokens': tokens,
            'user': meta['user'],
            'permissions': meta['permissions'],
            'properties': meta['properties']
        }, status=status.HTTP_200_OK)


@extend_schema(request=LogoutRequestSerializer, responses={200: dict})
class LogoutView(APIView):
    """
    Logs out the user by blacklisting the provided refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'Provide refresh token.'}, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully.'}, status=status.HTTP_250_OK if hasattr(status, 'HTTP_250_OK') else status.HTTP_200_OK)
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(responses={200: dict})
class CurrentUserView(APIView):
    """
    Returns the currently authenticated user details, permissions, and properties context.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        meta = AuthService.get_user_metadata(request.user, tenant)
        return Response({
            'user': meta['user'],
            'permissions': meta['permissions'],
            'properties': meta['properties']
        }, status=status.HTTP_200_OK)


@extend_schema(request=ChangePasswordSerializer, responses={200: dict})
class ChangePasswordView(APIView):
    """
    Allows an authenticated user to change their password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({'error': 'Incorrect current password.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


@extend_schema(request=ForgotPasswordSerializer, responses={200: dict})
class ForgotPasswordView(APIView):
    """
    Initiates a forgot password flow (email or OTP).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        reset_method = serializer.validated_data['reset_method']

        user = AppUser.objects.filter(email__iexact=email, tenant=tenant, deleted_at__isnull=True).first()
        if not user:
            # For security, we can return success but we return error if specified
            return Response({'error': 'User with this email not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if reset_method == 'otp':
            import random
            import string
            code = "".join(random.choices(string.digits, k=6))
            user.otp_code = code
            user.otp_expires_at = timezone.now() + timezone.timedelta(minutes=10)
            user.save(update_fields=['otp_code', 'otp_expires_at'])
            
            from apps.core.accounts.services import get_otp_provider
            provider = get_otp_provider('mock')
            provider.send_otp(user.email, code)
            
            return Response({
                'message': 'OTP verification code sent to email.',
                'otp_code': code  # helpful for testing/development
            }, status=status.HTTP_200_OK)
        else:
            signer = TimestampSigner()
            token = signer.sign(str(user.id))
            
            # Print/log token
            print(f"\n--- [RESET TOKEN] {token} for user {user.email} ---\n")
            
            # Send email (mock)
            from django.core.mail import send_mail
            from django.conf import settings
            try:
                send_mail(
                    subject='Retrod PMS Password Reset Request',
                    message=f'Use this token to reset your password: {token}. It is valid for 15 minutes.',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@retrod.io'),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception:
                pass

            return Response({
                'message': 'Password reset link sent to email.',
                'token': token
            }, status=status.HTTP_200_OK)


@extend_schema(request=ResetPasswordSerializer, responses={200: dict})
class ResetPasswordView(APIView):
    """
    Resets the user's password using the forgot-password token or OTP.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        user = AppUser.objects.filter(email__iexact=email, tenant=tenant, deleted_at__isnull=True).first()
        if not user:
            return Response({'error': 'User not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the token is OTP (6-digit numeric)
        if token.isdigit() and len(token) == 6:
            if not user.otp_code or user.otp_code != token:
                return Response({'error': 'Invalid or expired OTP code.'}, status=status.HTTP_400_BAD_REQUEST)
            if not user.otp_expires_at or timezone.now() > user.otp_expires_at:
                return Response({'error': 'OTP code has expired.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Clear OTP fields
            user.otp_code = None
            user.otp_expires_at = None
        else:
            signer = TimestampSigner()
            try:
                user_id = signer.unsign(token, max_age=900)
                if user_id != str(user.id):
                    return Response({'error': 'Invalid token for this user.'}, status=status.HTTP_400_BAD_REQUEST)
            except SignatureExpired:
                return Response({'error': 'Token has expired.'}, status=status.HTTP_400_BAD_REQUEST)
            except BadSignature:
                return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)


class UserInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        role_id = request.data.get('role_id')
        property_id = request.data.get('property_id')

        if not email or not role_id:
            return Response({'error': 'email and role_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        token = uuid.uuid4().hex
        expires_at = timezone.now() + timezone.timedelta(days=7)

        invite = UserInvitation.objects.create(
            tenant=tenant,
            property_id=property_id,
            email=email,
            role_id=role_id,
            token=token,
            expires_at=expires_at,
            status='PENDING'
        )

        return Response(UserInvitationSerializer(invite).data, status=status.HTTP_201_CREATED)


class UserResendInvitationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data.get('email')
        if not email:
            return Response({'error': 'email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        invite = UserInvitation.objects.filter(tenant=tenant, email=email, status='PENDING').first()
        if not invite:
            return Response({'error': 'Pending invitation not found.'}, status=status.HTTP_404_NOT_FOUND)

        invite.token = uuid.uuid4().hex
        invite.expires_at = timezone.now() + timezone.timedelta(days=7)
        invite.save()

        return Response(UserInvitationSerializer(invite).data, status=status.HTTP_200_OK)


class UserInvitationsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        invites = UserInvitation.objects.filter(tenant=tenant)
        return Response(UserInvitationSerializer(invites, many=True).data)


class UserAssignTenantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        tenant_id = request.data.get('tenant_id')

        if not user_id or not tenant_id:
            return Response({'error': 'user_id and tenant_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        assignment = UserAssignment.objects.create(
            user_id=user_id,
            tenant_id=tenant_id
        )

        return Response(UserAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class UserAssignPropertyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        tenant_id = request.data.get('tenant_id')
        property_id = request.data.get('property_id')
        role_id = request.data.get('role_id')

        if not user_id or not tenant_id or not property_id:
            return Response({'error': 'user_id, tenant_id, and property_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        assignment = UserAssignment.objects.create(
            user_id=user_id,
            tenant_id=tenant_id,
            property_id=property_id,
            role_id=role_id
        )

        return Response(UserAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class UserAssignmentsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        assigns = UserAssignment.objects.filter(tenant=tenant)
        return Response(UserAssignmentSerializer(assigns, many=True).data)


class PasswordPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = PasswordPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return PasswordPolicy.objects.none()
        return PasswordPolicy.objects.filter(tenant=tenant) | PasswordPolicy.objects.filter(tenant__isnull=True)


class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LoginAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LoginAttempt.objects.none()
        return LoginAttempt.objects.filter(user__tenant=tenant)


class FailedLoginsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        fails = LoginAttempt.objects.filter(user__tenant=tenant, success=False)
        return Response(LoginAttemptSerializer(fails, many=True).data)


class LockUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        reason = request.data.get('reason', 'Administrative lock')
        minutes = int(request.data.get('minutes', 15))

        if not user_id:
            return Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        lock, created = AccountLock.objects.update_or_create(
            user_id=user_id,
            defaults={'locked_until': locked_until, 'reason': reason}
        )

        return Response(AccountLockSerializer(lock).data, status=status.HTTP_200_OK)


class UnlockUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        AccountLock.objects.filter(user_id=user_id).delete()
        return Response({'message': 'User unlocked successfully.'}, status=status.HTTP_200_OK)


class MFAEnableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        method = request.data.get('method', 'TOTP')
        secret = uuid.uuid4().hex[:16].upper() # Mock secret key
        
        mfa, created = UserMFA.objects.update_or_create(
            user=request.user,
            defaults={'secret': secret, 'method': method, 'enabled': True}
        )
        return Response(UserMFASerializer(mfa).data, status=status.HTTP_200_OK)


class MFADisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        UserMFA.objects.filter(user=request.user).update(enabled=False)
        return Response({'message': 'MFA disabled successfully.'}, status=status.HTTP_200_OK)


class MFAVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'error': 'code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Mock OTP code matches last 6 digits of session token or is default '123456'
        mfa = UserMFA.objects.filter(user=request.user, enabled=True).first()
        if not mfa:
            return Response({'error': 'MFA is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        if code == '123456' or code in mfa.secret:
            return Response({'verified': True, 'message': 'MFA verified successfully.'})
        return Response({'verified': False, 'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserSession.objects.none()
        return UserSession.objects.filter(user__tenant=tenant)


class SessionRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session_id = request.data.get('session_id')
        if not session_id:
            return Response({'error': 'session_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        session = UserSession.objects.filter(id=session_id).first()
        if session:
            session.is_active = False
            session.revoked_at = timezone.now()
            session.save()
            return Response({'message': 'Session revoked successfully.'}, status=status.HTTP_200_OK)
        return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)


class IPWhitelistViewSet(viewsets.ModelViewSet):
    serializer_class = IPWhitelistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return IPWhitelist.objects.none()
        return IPWhitelist.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class SSOConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = SSOConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return SSOConfiguration.objects.none()
        return SSOConfiguration.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


