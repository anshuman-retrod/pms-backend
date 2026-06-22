from rest_framework import viewsets, permissions
from apps.core.audit.models import AuditLog
from apps.core.audit.serializers import AuditLogSerializer

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Tenant-isolated, read-only viewset for Audit logs.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return AuditLog.objects.none()
        return AuditLog.objects.filter(tenant=tenant).order_by('-timestamp')
