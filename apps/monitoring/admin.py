from django.contrib import admin
from apps.monitoring.models import SystemHealthSnapshot, SystemMetric

@admin.register(SystemHealthSnapshot)
class SystemHealthSnapshotAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'status', 'recorded_at')

@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_code', 'metric_value', 'recorded_at')
