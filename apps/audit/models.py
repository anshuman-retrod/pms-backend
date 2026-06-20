import uuid
from django.db import models
from apps.tenants.models import Tenant, Property
from django.conf import settings

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs')
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    actor_name = models.CharField(max_length=120)
    actor_role_code = models.CharField(max_length=64)
    
    action_type = models.CharField(max_length=64)  # LOGIN, LOGOUT, CREATED, UPDATED, DELETED, etc.
    target_entity = models.CharField(max_length=64)  # Tenant, Property, AppUser, etc.
    target_id = models.CharField(max_length=120)
    
    payload_before = models.JSONField(null=True, blank=True)
    payload_after = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, null=True, blank=True)
    device_info = models.JSONField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True, db_index=True)

    def __str__(self):
        return f"{self.timestamp} - {self.actor_name} performed {self.action_type} on {self.target_entity}"
