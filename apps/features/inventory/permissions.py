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
        # Fallback permission mapping (inventory settings are part of overall system settings)
        fallback_perm_code = 'settings.edit'
        if perm_code == 'inventory.view':
            fallback_perm_code = 'settings.view'

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        # Check for property ID in request context (prefer body payload for write actions)
        property_id = None
        if request.method in ['POST', 'PUT', 'PATCH'] and hasattr(request.data, 'get'):
            property_id = request.data.get('property_id') or request.data.get('property')
            
        if not property_id:
            property_id = request.headers.get('X-Property-ID') or request.query_params.get('property_id')
        if not property_id:
            property_id = view.kwargs.get('property_id')

        log_msg = f"DEBUG: method={request.method}, path={request.path}, property_id={property_id}, perm_code={perm_code}, fallback_perm_code={fallback_perm_code}, user={request.user}\n"
        with open('perm_debug.log', 'a') as f:
            f.write(log_msg)

        # If no specific property ID context is given, allow list operations if authorized for ANY property under the tenant
        if not property_id:
            user_roles = UserPropertyRole.objects.filter(user=request.user, tenant=tenant)
            with open('perm_debug.log', 'a') as f:
                f.write(f"DEBUG: no property_id, user_roles count={user_roles.count()}\n")
            for ur in user_roles:
                has_perm = ur.role.permissions.filter(permission__code__in=[perm_code, fallback_perm_code]).exists()
                with open('perm_debug.log', 'a') as f:
                    f.write(f"DEBUG: role={ur.role.name}, has_perm={has_perm}\n")
                if has_perm:
                    return True
            return False

        # Specific property checks
        user_property_role = UserPropertyRole.objects.filter(
            user=request.user,
            property_id=property_id,
            tenant=tenant
        ).first()

        with open('perm_debug.log', 'a') as f:
            f.write(f"DEBUG: user_property_role={user_property_role}\n")
        if not user_property_role:
            return False

        has_perm = user_property_role.role.permissions.filter(permission__code__in=[perm_code, fallback_perm_code]).exists()
        with open('perm_debug.log', 'a') as f:
            f.write(f"DEBUG: has_perm={has_perm}\n")
        return has_perm


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
