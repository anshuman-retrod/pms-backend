from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from apps.core.common.models import (
    SystemLanguage, SystemTax, SystemDocumentType,
    SystemCurrency, SystemDateFormat, SystemTimeFormat,
    Department, Shift, OccupancyType, BookingSource
)
from apps.core.common.serializers import (
    SystemLanguageSerializer, SystemTaxSerializer,
    SystemDocumentTypeSerializer, SystemCurrencySerializer,
    SystemDateFormatSerializer, SystemTimeFormatSerializer,
    DepartmentSerializer, ShiftSerializer, OccupancyTypeSerializer,
    BookingSourceSerializer
)

class SystemLanguageViewSet(viewsets.ModelViewSet):
    serializer_class = SystemLanguageSerializer
    queryset = SystemLanguage.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            SystemLanguage.objects.filter(is_default=True).update(is_default=False)
        serializer.save()

    def perform_update(self, serializer):
        is_default = serializer.validated_data.get('is_default', False)
        if is_default:
            SystemLanguage.objects.filter(is_default=True).update(is_default=False)
        serializer.save()


class TenantAwareSettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return self.queryset.filter(Q(tenant__isnull=True) | Q(tenant=tenant))
        return self.queryset

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        user = self.request.user
        is_super = getattr(user, 'is_superuser', False) or getattr(user, 'role', '') == 'SUPERADMIN'
        
        if is_super:
            tenant_id = self.request.data.get('tenant')
            if tenant_id:
                serializer.save(tenant_id=tenant_id)
            else:
                serializer.save(tenant=None)
        else:
            serializer.save(tenant=tenant)


class SystemTaxViewSet(TenantAwareSettingsViewSet):
    serializer_class = SystemTaxSerializer
    queryset = SystemTax.objects.all()


class SystemDocumentTypeViewSet(TenantAwareSettingsViewSet):
    serializer_class = SystemDocumentTypeSerializer
    queryset = SystemDocumentType.objects.all()



class SystemCurrencyViewSet(TenantAwareSettingsViewSet):
    serializer_class = SystemCurrencySerializer
    queryset = SystemCurrency.objects.all()


class SystemDateFormatViewSet(TenantAwareSettingsViewSet):
    serializer_class = SystemDateFormatSerializer
    queryset = SystemDateFormat.objects.all()


class SystemTimeFormatViewSet(TenantAwareSettingsViewSet):
    serializer_class = SystemTimeFormatSerializer
    queryset = SystemTimeFormat.objects.all()


class DepartmentViewSet(TenantAwareSettingsViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all()


class ShiftViewSet(TenantAwareSettingsViewSet):
    serializer_class = ShiftSerializer
    queryset = Shift.objects.all()


class OccupancyTypeViewSet(TenantAwareSettingsViewSet):
    serializer_class = OccupancyTypeSerializer
    queryset = OccupancyType.objects.all()


class BookingSourceViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSourceSerializer
    queryset = BookingSource.objects.all()

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
