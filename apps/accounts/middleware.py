from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from apps.accounts.models import AccountLock, IPWhitelist

class AccountLockoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            lock = AccountLock.objects.filter(user=user, locked_until__gt=timezone.now()).first()
            if lock:
                return JsonResponse({
                    'error': 'Account is temporarily locked.',
                    'reason': lock.reason,
                    'locked_until': lock.locked_until.isoformat()
                }, status=403)
        return None


class IPWhitelistMiddleware(MiddlewareMixin):
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def process_request(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None

        # Check if the path should bypass whitelisting
        path = request.path_info
        if path.startswith('/admin/') or path.startswith('/api/schema/'):
            return None

        # Check if IP whitelist enforcement is enabled for the tenant
        config = getattr(tenant, 'configuration', None)
        if not config or not getattr(config, 'enforce_ip_whitelist', False):
            return None

        # Retrieve whitelist for tenant
        whitelist = IPWhitelist.objects.filter(tenant=tenant)
        if not whitelist.exists():
            return None

        client_ip = self.get_client_ip(request)
        allowed_ips = [w.ip_address for w in whitelist]

        # Simple string inclusion or exact match
        if client_ip not in allowed_ips and '0.0.0.0' not in allowed_ips:
            # Check if there is an IP pattern or match
            return JsonResponse({
                'error': f'Access denied: IP {client_ip} is not whitelisted for tenant {tenant.name}.'
            }, status=403)

        return None
