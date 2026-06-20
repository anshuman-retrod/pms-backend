from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Import Views
from apps.tenants.views import (
    TenantViewSet, PropertyViewSet, TenantBrandingViewSet, TenantDomainViewSet,
    TenantConfigurationViewSet, TenantIsolationConfigViewSet
)
from apps.properties.views import (
    PropertyConfigurationViewSet, PropertyContactViewSet
)
from apps.rbac.views import RoleViewSet, PermissionViewSet, RolePermissionViewSet, UserPropertyRoleViewSet
from apps.accounts.views import (
    UserViewSet, PasswordLoginView, RequestOTPView, 
    VerifyOTPView, LogoutView, CurrentUserView,
    ChangePasswordView, ForgotPasswordView, ResetPasswordView,
    UserInviteView, UserResendInvitationView, UserInvitationsListView,
    UserAssignTenantView, UserAssignPropertyView, UserAssignmentsListView,
    PasswordPolicyViewSet, LoginAttemptViewSet, FailedLoginsListView,
    LockUserView, UnlockUserView, MFAEnableView, MFADisableView, MFAVerifyView,
    SessionViewSet, SessionRevokeView, IPWhitelistViewSet, SSOConfigurationViewSet
)
from apps.audit.views import AuditLogViewSet
from apps.inventory.views import BuildingViewSet, FloorViewSet, FloorPlanViewSet
from apps.subscriptions.views import (
    ProductViewSet, ProductFeatureViewSet, LicenseViewSet,
    EntitlementViewSet, UsageViewSet
)

# Initialize DRF Router
router = DefaultRouter()

# Tenants & Properties
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'tenant-branding', TenantBrandingViewSet, basename='tenantbranding')
router.register(r'tenant-domains', TenantDomainViewSet, basename='tenantdomain')
router.register(r'tenant-configurations', TenantConfigurationViewSet, basename='tenantconfiguration')
router.register(r'tenant-isolation', TenantIsolationConfigViewSet, basename='tenantisolation')
router.register(r'property-configurations', PropertyConfigurationViewSet, basename='propertyconfiguration')
router.register(r'property-contacts', PropertyContactViewSet, basename='propertycontact')

# RBAC
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'role-permissions', RolePermissionViewSet, basename='rolepermission')
router.register(r'user-property-roles', UserPropertyRoleViewSet, basename='userpropertyrole')

# Accounts
router.register(r'users', UserViewSet, basename='user')

# Audit Logs
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

# Building & Floor Management
router.register(r'buildings', BuildingViewSet, basename='building')
router.register(r'floors', FloorViewSet, basename='floor')
router.register(r'floor-plans', FloorPlanViewSet, basename='floorplan')

# Product Access & License Engine
router.register(r'products', ProductViewSet, basename='main_product')
router.register(r'product-features', ProductFeatureViewSet, basename='main_product_feature')
router.register(r'licenses', LicenseViewSet, basename='main_license')
router.register(r'entitlements', EntitlementViewSet, basename='main_entitlement')
router.register(r'usage', UsageViewSet, basename='main_usage')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Base Viewsets
    path('api/', include(router.urls)),
    
    # Inventory Domain Endpoints
    path('api/inventory/', include('apps.inventory.urls')),
    
    # Availability Domain Endpoints
    path('api/', include('apps.availability.urls')),
    
    # Rate Management Domain Endpoints
    path('api/rates/', include('apps.rates.urls')),
    
    # Guest CRM Domain Endpoints
    path('api/crm/', include('apps.crm.urls')),
    
    # Global Reference Data Endpoints
    path('api/reference/', include('apps.reference.urls')),
    
    # Reservation Domain Endpoints
    path('api/reservations/', include('apps.reservations.urls')),

    # Subscription & Entitlement Module Endpoints
    path('api/subscriptions/', include('apps.subscriptions.urls')),

    # Asset Management Endpoints
    path('api/assets/', include('apps.assets.urls')),

    # Maintenance Management Endpoints
    path('api/maintenance/', include('apps.maintenance.urls')),

    # Compliance & Governance Endpoints
    path('api/compliance/', include('apps.compliance.urls')),

    # Monitoring & Administration Endpoints
    path('api/admin/', include('apps.monitoring.urls')),
    
    # Custom Auth Endpoints
    path('api/auth/login/', PasswordLoginView.as_view(), name='password_login'),
    path('api/auth/request-otp/', RequestOTPView.as_view(), name='request_otp'),
    path('api/auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/me/', CurrentUserView.as_view(), name='current_user'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('api/auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('api/auth/reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    
    # User Invitation & Assignment
    path('api/users/invite/', UserInviteView.as_view(), name='user_invite'),
    path('api/users/resend-invitation/', UserResendInvitationView.as_view(), name='user_resend_invite'),
    path('api/users/invitations/', UserInvitationsListView.as_view(), name='user_invitations_list'),
    path('api/users/assign-tenant/', UserAssignTenantView.as_view(), name='user_assign_tenant'),
    path('api/users/assign-property/', UserAssignPropertyView.as_view(), name='user_assign_property'),
    path('api/users/assignments/', UserAssignmentsListView.as_view(), name='user_assignments_list'),

    # Security & Protection
    path('api/security/password-policy/', PasswordPolicyViewSet.as_view({'get': 'list', 'put': 'update'}), name='password_policy'),
    path('api/security/login-attempts/', LoginAttemptViewSet.as_view({'get': 'list'}), name='login_attempts'),
    path('api/security/failed-logins/', FailedLoginsListView.as_view(), name='failed_logins'),
    path('api/security/lock-user/', LockUserView.as_view(), name='lock_user'),
    path('api/security/unlock-user/', UnlockUserView.as_view(), name='unlock_user'),
    
    # MFA & Sessions
    path('api/security/mfa/enable/', MFAEnableView.as_view(), name='mfa_enable'),
    path('api/security/mfa/disable/', MFADisableView.as_view(), name='mfa_disable'),
    path('api/security/mfa/verify/', MFAVerifyView.as_view(), name='mfa_verify'),
    path('api/security/sessions/', SessionViewSet.as_view({'get': 'list'}), name='sessions'),
    path('api/security/sessions/revoke/', SessionRevokeView.as_view(), name='session_revoke'),
    
    # IP Whitelisting & SSO Config
    path('api/security/ip-whitelist/', IPWhitelistViewSet.as_view({'get': 'list', 'post': 'create'}), name='ip_whitelist'),
    path('api/security/ip-whitelist/<uuid:pk>/', IPWhitelistViewSet.as_view({'delete': 'destroy'}), name='ip_whitelist_detail'),
    path('api/security/sso/', SSOConfigurationViewSet.as_view({'get': 'list', 'post': 'create'}), name='sso_list'),
    path('api/security/sso/<uuid:pk>/', SSOConfigurationViewSet.as_view({'put': 'update'}), name='sso_detail'),
    
    # OpenAPI Schema & Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
