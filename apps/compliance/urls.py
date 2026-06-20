from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.compliance.views import (
    ConsentRecordViewSet, RetentionPolicyViewSet, GDPRRequestViewSet,
    ExportTenantView, ExportGuestView
)

router = DefaultRouter()
router.register(r'consents', ConsentRecordViewSet, basename='consent')
router.register(r'retention-policies', RetentionPolicyViewSet, basename='retentionpolicy')
router.register(r'gdpr-request', GDPRRequestViewSet, basename='gdprrequest')

urlpatterns = [
    path('', include(router.urls)),
    path('export-tenant/', ExportTenantView.as_view(), name='export_tenant'),
    path('export-guest/', ExportGuestView.as_view(), name='export_guest'),
]
