from rest_framework import viewsets, permissions, pagination
from apps.core.audit.models import AuditLog
from apps.core.audit.serializers import AuditLogSerializer
from django.utils import timezone
from datetime import timedelta

class AuditLogPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Tenant-isolated, read-only viewset for Audit logs.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', getattr(self.request, 'tenant', None))
        if not tenant:
            return AuditLog.objects.none()
        
        queryset = AuditLog.objects.filter(tenant=tenant)
        
        # Filter for last 24 hours if last_24_hours=true
        last_24 = self.request.query_params.get('last_24_hours', 'false').lower() == 'true'
        if last_24:
            cutoff = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=cutoff)
            
        return queryset.order_by('-timestamp')
