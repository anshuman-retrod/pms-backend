from rest_framework import viewsets, permissions
from apps.tenants.models import (
    Tenant, Property, TenantBranding, TenantDomain, 
    TenantConfiguration, TenantIsolationConfig
)
from apps.tenants.serializers import (
    TenantSerializer, PropertySerializer, TenantBrandingSerializer, TenantDomainSerializer,
    TenantConfigurationSerializer, TenantIsolationConfigSerializer
)

class TenantViewSet(viewsets.ModelViewSet):
    """
    Super-Admin CRUD endpoint for managing Tenants.
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAdminUser]  # Only django admin/superusers can manage tenants directly

class PropertyViewSet(viewsets.ModelViewSet):
    """
    CRUD endpoint for managing Properties under the resolved tenant context.
    """
    serializer_class = PropertySerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Property.objects.none()
        return Property.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(
            tenant=tenant,
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
        
    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user if self.request.user.is_authenticated else None
        )


class TenantBrandingViewSet(viewsets.ModelViewSet):
    serializer_class = TenantBrandingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantBranding.objects.none()
        return TenantBranding.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class TenantDomainViewSet(viewsets.ModelViewSet):
    serializer_class = TenantDomainSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantDomain.objects.none()
        return TenantDomain.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class TenantConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = TenantConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantConfiguration.objects.none()
        return TenantConfiguration.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class TenantIsolationConfigViewSet(viewsets.ModelViewSet):
    serializer_class = TenantIsolationConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return TenantIsolationConfig.objects.none()
        return TenantIsolationConfig.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)

