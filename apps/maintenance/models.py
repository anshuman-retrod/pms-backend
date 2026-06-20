import uuid
from django.db import models
from apps.tenants.models import Tenant, Property
from apps.inventory.models import InventoryUnit
from apps.assets.models import Asset
from django.conf import settings

class MaintenanceTicket(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    )
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='maintenance_tickets')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='maintenance_tickets')
    inventory_unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='maintenance_tickets')
    asset = models.ForeignKey(Asset, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_tickets')
    title = models.CharField(max_length=120)
    description = models.TextField()
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='OPEN')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_tickets'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'maintenance_ticket'

    def __str__(self):
        return f"Ticket #{self.title} ({self.status})"


class MaintenanceSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='schedules')
    schedule_type = models.CharField(max_length=64) # e.g. PREVENTATIVE, INSPECTION
    next_due_date = models.DateField()

    class Meta:
        db_table = 'maintenance_schedule'

    def __str__(self):
        return f"{self.asset.asset_name} - {self.schedule_type} due on {self.next_due_date}"
