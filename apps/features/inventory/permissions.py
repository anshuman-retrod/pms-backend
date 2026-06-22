from rest_framework import permissions
from apps.core.rbac.models import UserPropertyRole

class HasInventoryPermission(permissions.BasePermission):
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
        if view.action in ['list', 'retrieve']:
            return 'inventory.view'
        elif view.action == 'create':
            return 'inventory.create'
        elif view.action in ['update', 'partial_update']:
            return 'inventory.edit'
        elif view.action == 'destroy':
            return 'inventory.delete'
        
        return 'inventory.view'

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

        # If no specific property ID context is given, allow list operations if authorized for ANY property under the tenant
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


class IsAmenityManager(HasInventoryPermission):
    def get_required_permission(self, request, view):
        return 'amenity.manage'


class IsAttributeManager(HasInventoryPermission):
    def get_required_permission(self, request, view):
        return 'attribute.manage'


class CanCloneInventoryType(HasInventoryPermission):
    def get_required_permission(self, request, view):
        return 'inventory_type.clone'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        pk = view.kwargs.get('pk')
        if not pk:
            return False

        from apps.features.inventory.models import InventoryUnitType
        try:
            source = InventoryUnitType.objects.all_with_deleted().get(id=pk)
            if source.tenant != tenant:
                return False
            property_id = source.property_id
        except Exception:
            return False

        user_property_role = UserPropertyRole.objects.filter(
            user=request.user,
            property_id=property_id,
            tenant=tenant
        ).first()

        if not user_property_role:
            return False

        return user_property_role.role.permissions.filter(permission__code='inventory_type.clone').exists()
