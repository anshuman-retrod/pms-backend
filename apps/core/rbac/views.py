from rest_framework import viewsets, permissions
from django.db.models import Q
from apps.core.rbac.models import Permission, Role, RolePermission, UserPropertyRole
from apps.core.rbac.serializers import PermissionSerializer, RoleSerializer, RolePermissionSerializer, UserPropertyRoleSerializer

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Permission catalog.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

class RoleViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for Roles. Displays both global roles and tenant-specific roles.
    """
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        user = self.request.user
        is_super = getattr(user, 'is_superuser', False) or getattr(user, 'role', '') == 'SUPERADMIN'
        
        # Exclude superadmin and owner roles from regular tenant views
        qs = Role.objects.all()
        if not is_super:
            qs = qs.exclude(code__in=['super_admin', 'owner'])
            
        if not tenant:
            return qs.filter(tenant__isnull=True)
        # Return global roles + roles specific to this tenant
        return qs.filter(Q(tenant__isnull=True) | Q(tenant=tenant))

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)

class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset linking Permissions to Roles.
    """
    serializer_class = RolePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return RolePermission.objects.filter(role__tenant__isnull=True)
        return RolePermission.objects.filter(
            Q(role__tenant__isnull=True) | Q(role__tenant=tenant)
        )

class UserPropertyRoleViewSet(viewsets.ModelViewSet):
    """
    CRUD Viewset for assigning Roles to Users per Property scope.
    """
    serializer_class = UserPropertyRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return UserPropertyRole.objects.none()
        return UserPropertyRole.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)
