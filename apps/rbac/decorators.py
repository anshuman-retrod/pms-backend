from functools import wraps
from django.http import JsonResponse
from apps.rbac.models import UserPropertyRole

def check_property_access(user, tenant, property_id):
    """
    Checks if a user has access to a specific property.
    Superusers bypass checking.
    """
    if not user.is_authenticated:
        return False
        
    # Superusers bypass property checks
    if user.is_superuser:
        return True
        
    # Check if user is linked to the property under the tenant
    return UserPropertyRole.objects.filter(
        user=user,
        property_id=property_id,
        tenant=tenant
    ).exists()

def require_property_access(property_id_param='property_id'):
    """
    Decorator for views that checks if the logged-in user has access
    to the property specified in the request.
    It checks URL kwargs, GET parameters, or X-Property-ID header.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication credentials were not provided.'}, status=401)

            # Retrieve property_id
            property_id = kwargs.get(property_id_param)
            if not property_id:
                property_id = request.GET.get(property_id_param)
            if not property_id:
                property_id = request.headers.get('X-Property-ID')

            if not property_id:
                return JsonResponse({'error': 'Property ID context is missing. Provide property_id parameter or X-Property-ID header.'}, status=400)

            # Resolve tenant
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                return JsonResponse({'error': 'Tenant context is missing.'}, status=400)

            # Check access
            if not check_property_access(request.user, tenant, property_id):
                return JsonResponse({'error': f'You do not have access to property with ID {property_id}.'}, status=403)

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
