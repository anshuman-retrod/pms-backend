from rest_framework import permissions
from apps.rbac.models import UserPropertyRole

class HasGuestPermission(permissions.BasePermission):
    """
    DRF permission class that validates if the authenticated user
    has the required permission for the resolved property context.
    Superusers bypass checking.
    """
    def __init__(self, required_permission=None):
        super().__init__()
        self.required_permission = required_permission

    def get_required_permission(self, request, view):
        if self.required_permission:
            return self.required_permission
        
        # Fallback mapping based on standard REST framework view actions
        if view.action in ['list', 'retrieve', 'search', 'activities', 'active']:
            return 'guest.view'
        elif view.action == 'create':
            return 'guest.create'
        elif view.action in ['update', 'partial_update']:
            return 'guest.edit'
        elif view.action == 'destroy':
            return 'guest.delete'
        
        return 'guest.view'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        perm_code = self.get_required_permission(request, view)
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        # Check for property ID in request context
        property_id = request.headers.get('X-Property-ID') or request.query_params.get('property_id')
        if not property_id:
            property_id = view.kwargs.get('property_id')
        
        # In CRM endpoints, if no property context is given, allow operations if authorized for ANY property under the tenant
        if not property_id:
            user_roles = UserPropertyRole.objects.filter(user=request.user, tenant=tenant)
            for ur in user_roles:
                if ur.role.permissions.filter(permission__code=perm_code).exists():
                    return True
            return False

        # Specific property checks
        user_property_role = UserPropertyRole.objects.filter(
            user=request.user,
            property_id=property_id,
            tenant=tenant
        ).first()

        if not user_property_role:
            return False

        return user_property_role.role.permissions.filter(permission__code=perm_code).exists()


class IsMergeManager(HasGuestPermission):
    def get_required_permission(self, request, view):
        return 'guest.merge'


class IsVerifyDocumentManager(HasGuestPermission):
    def get_required_permission(self, request, view):
        return 'guest.verify_document'


class IsLoyaltyManager(HasGuestPermission):
    def get_required_permission(self, request, view):
        return 'guest.manage_loyalty'


class IsTagManager(HasGuestPermission):
    def get_required_permission(self, request, view):
        return 'guest.manage_tags'
