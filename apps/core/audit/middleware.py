import uuid
import json
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from apps.core.audit.models import AuditLog
from apps.core.rbac.models import UserPropertyRole

class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Generate and attach a unique request trace ID
        request.request_id = uuid.uuid4()
        
        # Store initial body for PUT/POST/PATCH payloads to record 'payload_before' or 'payload_after'
        request._audit_payload_before = None
        
        # In a real environment, resolving 'payload_before' requires querying the database
        # before mutation. For this foundation release, we will capture request bodies and response data.
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Cache request body without breaking stream read
                request._audit_body = request.body.decode('utf-8')
            except Exception:
                request._audit_body = None
        else:
            request._audit_body = None

    def process_response(self, request, response):
        # Only audit mutation API endpoints (exclude schemas, static, templates)
        path = request.path_info
        if not path.startswith('/api/'):
            return response

        # Resolve tenant context
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return response

        # We want to audit mutations (POST, PUT, PATCH, DELETE) or successful auth logs
        is_mutation = request.method in ['POST', 'PUT', 'PATCH', 'DELETE']
        is_auth_endpoint = any(kw in path for kw in ['login', 'verify-otp', 'logout'])

        if not (is_mutation or is_auth_endpoint):
            return response

        # Check response success
        # For mutations, we generally log successfully completed actions (status codes 2xx)
        # Auth endpoints are logged in both success and failure cases (auth audits failures)
        if is_mutation and not (200 <= response.status_code < 300):
            return response

        # Extract actor metadata
        user = request.user
        actor_name = "Anonymous"
        actor_role = "Anonymous"
        actor_user = None

        if user and user.is_authenticated:
            actor_user = user
            actor_name = user.name
            
            # Resolve active role for property scope
            property_id = request.headers.get('X-Property-ID') or request.GET.get('property_id')
            if user.is_superuser:
                actor_role = "super_admin"
            elif property_id:
                try:
                    upr = UserPropertyRole.objects.filter(user=user, property_id=property_id, tenant=tenant).first()
                    if upr:
                        actor_role = upr.role.code
                except Exception:
                    pass
            else:
                # Fallback to first role found for this tenant
                upr = UserPropertyRole.objects.filter(user=user, tenant=tenant).first()
                if upr:
                    actor_role = upr.role.code
        elif is_auth_endpoint:
            resolved_from_response = False
            if response.status_code == 200:
                try:
                    resp_data = getattr(response, 'data', None)
                    if not resp_data and hasattr(response, 'content'):
                        resp_data = json.loads(response.content.decode('utf-8'))
                    if isinstance(resp_data, dict) and 'user' in resp_data:
                        user_meta = resp_data['user']
                        user_id = user_meta.get('id')
                        if user_id:
                            from apps.core.accounts.models import AppUser
                            actor_user = AppUser.objects.filter(id=user_id).first()
                            if actor_user:
                                actor_name = actor_user.name
                                actor_role = user_meta.get('role') or "Anonymous"
                                resolved_from_response = True
                except Exception:
                    pass

            if not resolved_from_response:
                # If we are resolving auth endpoints, try to get the contact name/email from the input body
                try:
                    body_data = json.loads(request._audit_body) if request._audit_body else {}
                    actor_name = body_data.get('email_or_username') or body_data.get('email') or body_data.get('phone') or "Anonymous"
                except Exception:
                    pass

        # Action Type and Targets Mapping
        action_type = f"{request.method} {path}"
        target_entity = "API"
        target_id = "N/A"

        # Refine fields based on URLs
        if 'login' in path:
            action_type = "LOGIN"
            target_entity = "Auth"
        elif 'verify-otp' in path:
            action_type = "OTP_VERIFY"
            target_entity = "Auth"
        elif 'logout' in path:
            action_type = "LOGOUT"
            target_entity = "Auth"

        # Payloads
        payload_after = None
        if request._audit_body:
            try:
                payload_after = json.loads(request._audit_body)
                # Strip password field for safety
                if isinstance(payload_after, dict):
                    for secret in ['password', 'otp', 'otp_code']:
                        if secret in payload_after:
                            payload_after[secret] = "********"
            except Exception:
                payload_after = {"raw": request._audit_body}

        # IP Address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # User Agent
        ua = request.META.get('HTTP_USER_AGENT', '')

        # Property context
        property_id = request.headers.get('X-Property-ID') or request.GET.get('property_id')
        if not property_id and payload_after and isinstance(payload_after, dict):
            property_id = payload_after.get('property_id') or payload_after.get('property')

        # Log to db
        try:
            AuditLog.objects.create(
                tenant=tenant,
                property_id=property_id if property_id else None,
                actor_user=actor_user,
                actor_name=actor_name[:120],
                actor_role_code=actor_role[:64],
                action_type=action_type[:64],
                target_entity=target_entity[:64],
                target_id=str(target_id)[:120],
                payload_after=payload_after,
                ip_address=ip,
                user_agent=ua[:512],
                request_id=getattr(request, 'request_id', None)
            )
        except Exception as e:
            # Silently catch log errors so it never halts actual operational transactions
            import sys
            print(f"FAILED TO WRITE AUDIT LOG: {e}", file=sys.stderr)

        return response
