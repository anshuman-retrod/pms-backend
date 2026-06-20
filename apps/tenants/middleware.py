from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from apps.tenants.models import Tenant

class TenantResolutionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Allow accessing public schemas or swagger pages if desired, but let's enforce tenant resolution
        # on all api calls except admin panel login/schema, or exclude them dynamically.
        path = request.path_info
        
        # Paths that bypass tenant resolution (e.g., swagger docs, admin panels)
        bypass_paths = [
            '/admin/',
            '/api/schema/',
            '/favicon.ico',
        ]
        
        if any(path.startswith(bp) for bp in bypass_paths):
            request.tenant = None
            return None

        # 1. Resolve subdomain
        # First check custom header (excellent for local testing/postman)
        subdomain = request.headers.get('X-Tenant-Subdomain')
        
        # If header not present, resolve from host header
        if not subdomain:
            host = request.get_host().split(':')[0]  # strip port if exists
            
            # Skip domain parsing if accessing via localhost or raw IP address
            import re
            is_ip_or_localhost = host == 'localhost' or re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host)
            
            if not is_ip_or_localhost:
                host_parts = host.split('.')
                # Assuming standard structure e.g., subdomain.domain.com
                if len(host_parts) >= 3:
                    subdomain = host_parts[0]

        # In case we can't find a subdomain (e.g. localhost:8000), let's see if it's passed as a query param
        if not subdomain:
            subdomain = request.GET.get('subdomain')

        # Fallback to default tenant 'grandpalace' in local DEBUG mode to simplify Swagger UI/Postman testing
        if not subdomain and settings.DEBUG:
            subdomain = 'grandpalace'

        if not subdomain:
            return JsonResponse(
                {'error': 'Tenant subdomain resolution failed. Provide X-Tenant-Subdomain header, subdomain query parameter, or subdomain host.'},
                status=400
            )

        # 2. Query tenant
        try:
            tenant = Tenant.objects.get(subdomain=subdomain)
        except Tenant.DoesNotExist:
            return JsonResponse({'error': f'Tenant with subdomain "{subdomain}" does not exist.'}, status=404)

        # 3. Check tenant status
        if tenant.status == 'suspended':
            return JsonResponse({'error': 'Tenant account is suspended.'}, status=403)
        elif tenant.status == 'terminated':
            return JsonResponse({'error': 'Tenant account has been terminated.'}, status=403)
        elif tenant.status != 'active':
            return JsonResponse({'error': 'Tenant account is inactive.'}, status=403)

        # Attach tenant to request context
        request.tenant = tenant
        return None
