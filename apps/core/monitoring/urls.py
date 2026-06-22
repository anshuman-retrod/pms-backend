from django.urls import path
from apps.core.monitoring.views import (
    SecurityDashboardView, TenantDashboardView,
    SystemHealthView, SystemUsageView
)

urlpatterns = [
    path('security-dashboard/', SecurityDashboardView.as_view(), name='security_dashboard'),
    path('tenant-dashboard/', TenantDashboardView.as_view(), name='tenant_dashboard'),
    path('system-health/', SystemHealthView.as_view(), name='system_health'),
    path('system-usage/', SystemUsageView.as_view(), name='system_usage'),
]
