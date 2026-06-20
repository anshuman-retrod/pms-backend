from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.accounts.models import AppUser

@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'username', 'tenant', 'is_active', 'is_staff')
    search_fields = ('email', 'name', 'username')
    list_filter = ('tenant', 'is_active', 'is_staff')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name', 'username', 'phone', 'avatar_url', 'tenant')}),
        ('Preferences', {'fields': ('preferred_language', 'preferred_timezone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('OTP & Security', {'fields': ('otp_secret', 'otp_code', 'otp_expires_at', 'failed_login_attempts', 'lockout_expires_at')}),
        ('Audit Metadata', {'fields': ('created_by', 'updated_by', 'deleted_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
