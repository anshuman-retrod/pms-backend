from django.contrib import admin
from apps.maintenance.models import MaintenanceTicket, MaintenanceSchedule

@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority', 'status', 'assigned_to', 'inventory_unit', 'property', 'tenant')
    list_filter = ('priority', 'status', 'property')
    search_fields = ('title', 'description')

@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ('asset', 'schedule_type', 'next_due_date')
    list_filter = ('schedule_type',)
