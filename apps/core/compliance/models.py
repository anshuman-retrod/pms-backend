import uuid
from django.db import models
from apps.core.tenants.models import Tenant

class ConsentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='consent_records')
    guest = models.ForeignKey('crm.GuestProfile', on_delete=models.CASCADE, related_name='consent_records')
    consent_type = models.CharField(max_length=64) # e.g. MARKETING, COOKIES, THIRD_PARTY
    granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'consent_record'

    def __str__(self):
        return f"{self.guest.first_name} - {self.consent_type}: {self.granted}"


class RetentionPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='retention_policies', null=True, blank=True)
    entity_name = models.CharField(max_length=120) # e.g. RESERVATION, GUEST_PROFILE, INVOICE
    retention_days = models.IntegerField(default=365)
    archive_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = 'retention_policy'
        unique_together = ('tenant', 'entity_name')

    def __str__(self):
        return f"{self.entity_name} ({self.retention_days} days) - Archive: {self.archive_enabled}"


class GDPRRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='gdpr_requests')
    guest = models.ForeignKey('crm.GuestProfile', on_delete=models.CASCADE, related_name='gdpr_requests')
    request_type = models.CharField(max_length=32) # EXPORT, DELETE, ANONYMIZE
    status = models.CharField(max_length=32, default='PENDING') # PENDING, IN_PROGRESS, COMPLETED, REJECTED
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    soft_deleted_at = models.DateTimeField(null=True, blank=True)
    anonymized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'gdpr_request'

    def __str__(self):
        return f"{self.request_type} request for {self.guest.first_name} ({self.status})"
