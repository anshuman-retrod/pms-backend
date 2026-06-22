import uuid
from django.db import models
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnit

class Asset(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('MAINTENANCE', 'Maintenance'),
        ('DECOMMISSIONED', 'Decommissioned'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='assets')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='assets')
    asset_code = models.CharField(max_length=64, db_index=True)
    asset_name = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=64) # e.g. TV, AC, REFRIGERATOR, BED, SOFA, WARDROBE
    serial_number = models.CharField(max_length=120, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asset'
        unique_together = ('property', 'asset_code')

    def __str__(self):
        return f"{self.asset_name} ({self.asset_code})"


class AssetAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='assignments')
    inventory_unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='asset_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'asset_assignment'

    def __str__(self):
        return f"{self.asset.asset_name} -> {self.inventory_unit.name}"
