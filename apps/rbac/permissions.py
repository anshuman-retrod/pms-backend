from rest_framework import permissions
from apps.rbac.decorators import check_property_access

class HasPropertyAccess(permissions.BasePermission):
    """
    DRF permission class that validates whether the authenticated user
    has access to the specified property in the request context.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Superusers can access all properties
        if request.user.is_superuser:
            return True

        property_id = request.headers.get('X-Property-ID') or request.query_params.get('property_id')
        if not property_id:
            # If no property ID is provided in headers/query params, check if property_id is in view kwargs
            property_id = view.kwargs.get('property_id')

        # If property context is not required/provided, let it pass (rely on standard IsAuthenticated)
        if not property_id:
            return True

        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return False

        return check_property_access(request.user, tenant, property_id)
