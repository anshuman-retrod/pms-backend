from rest_framework import serializers
from apps.accounts.models import (
    AppUser, UserInvitation, UserAssignment, PasswordPolicy, LoginAttempt,
    AccountLock, UserMFA, UserSession, IPWhitelist, SSOConfiguration
)

class AppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = (
            'id', 'tenant', 'name', 'username', 'email', 'phone', 
            'avatar_url', 'preferred_language', 'preferred_timezone', 
            'is_active', 'is_staff', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_staff')

class AppUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AppUser
        fields = (
            'id', 'tenant', 'name', 'username', 'email', 'phone', 
            'avatar_url', 'preferred_language', 'preferred_timezone', 
            'is_active', 'password'
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        email = validated_data.pop('email', None)
        user = AppUser.objects.create_user(
            email=email,
            password=password,
            **validated_data
        )
        return user

class PasswordLoginRequestSerializer(serializers.Serializer):
    email_or_username = serializers.CharField(required=True, help_text="Email or Username of staff member")
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

class RequestOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, help_text="Email to dispatch code")
    phone = serializers.CharField(required=False, help_text="Phone to dispatch code")
    contact = serializers.CharField(required=False, help_text="General contact identifier")
    provider = serializers.ChoiceField(choices=['mock', 'email', 'sms'], required=False, help_text="OTP provider backend to use (defaults to configured system provider)")

class VerifyOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    contact = serializers.CharField(required=False)
    otp_code = serializers.CharField(required=True, help_text="6-digit verification code")

class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True, help_text="SimpleJWT refresh token to blacklist")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="Email of user requesting password reset")
    reset_method = serializers.ChoiceField(choices=['email', 'otp'], default='email', help_text="Reset flow type")


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    token = serializers.CharField(required=True, help_text="One-time token or OTP code received")
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class UserInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInvitation
        fields = '__all__'


class UserAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAssignment
        fields = '__all__'


class PasswordPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PasswordPolicy
        fields = '__all__'


class LoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginAttempt
        fields = '__all__'


class AccountLockSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountLock
        fields = '__all__'


class UserMFASerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMFA
        fields = '__all__'


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = '__all__'


class IPWhitelistSerializer(serializers.ModelSerializer):
    class Meta:
        model = IPWhitelist
        fields = '__all__'


class SSOConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSOConfiguration
        fields = '__all__'


