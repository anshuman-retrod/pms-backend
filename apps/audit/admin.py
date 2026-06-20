from django.contrib import admin
from apps.audit.models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'tenant', 'actor_name', 'actor_role_code', 'action_type', 'target_entity')
    search_fields = ('actor_name', 'action_type', 'target_entity', 'target_id')
    list_filter = ('tenant', 'action_type', 'target_entity')
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
