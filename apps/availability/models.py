from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import BaseModel
from apps.tenants.models import Tenant, Property
from apps.inventory.models import InventoryUnitType, InventoryUnit

class InventoryAvailability(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='availabilities')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='availabilities')
    date = models.DateField()
    inventory_unit_type = models.ForeignKey(InventoryUnitType, on_delete=models.CASCADE, related_name='availabilities')
    
    allocated_count = models.IntegerField(default=0)
    sold_count = models.IntegerField(default=0)
    blocked_count = models.IntegerField(default=0)
    overbooking_limit = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Inventory Availabilities'
        constraints = [
            models.UniqueConstraint(fields=['property', 'date', 'inventory_unit_type'], name='unique_property_date_unittype'),
            models.CheckConstraint(check=models.Q(allocated_count__gte=0), name='allocated_count_non_negative'),
            models.CheckConstraint(check=models.Q(sold_count__gte=0), name='sold_count_non_negative'),
            models.CheckConstraint(check=models.Q(blocked_count__gte=0), name='blocked_count_non_negative'),
            models.CheckConstraint(check=models.Q(overbooking_limit__gte=0), name='overbooking_limit_non_negative'),
        ]
        indexes = [
            models.Index(fields=['property', 'inventory_unit_type', 'date'], name='idx_prop_unittype_date'),
            models.Index(fields=['property', 'date'], name='idx_prop_date'),
        ]

    def clean(self):
        if self.property.tenant != self.tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")
        if self.inventory_unit_type.tenant != self.tenant:
            raise ValidationError("Inventory unit type must belong to the resolved tenant context.")
        if self.allocated_count < 0:
            raise ValidationError("Allocated count cannot be negative.")
        if self.sold_count < 0:
            raise ValidationError("Sold count cannot be negative.")
        if self.blocked_count < 0:
            raise ValidationError("Blocked count cannot be negative.")
        if self.overbooking_limit < 0:
            raise ValidationError("Overbooking limit cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.property.name} - {self.inventory_unit_type.code} @ {self.date}: {self.allocated_count}"


class InventoryRestriction(BaseModel):
    RESTRICTION_TYPE_CHOICES = (
        ('CTA', 'Closed to Arrival'),
        ('CTD', 'Closed to Departure'),
        ('STOP_SELL', 'Stop Sell'),
        ('MIN_LOS', 'Minimum Length of Stay'),
        ('MAX_LOS', 'Maximum Length of Stay'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='restrictions')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='restrictions')
    date = models.DateField()
    inventory_unit_type = models.ForeignKey(InventoryUnitType, on_delete=models.CASCADE, null=True, blank=True, related_name='restrictions')
    rate_plan_id = models.UUIDField(null=True, blank=True)
    restriction_type = models.CharField(max_length=32, choices=RESTRICTION_TYPE_CHOICES)
    restriction_value = models.IntegerField(null=True, blank=True)

    def clean(self):
        if self.property.tenant != self.tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")
        if self.inventory_unit_type and self.inventory_unit_type.tenant != self.tenant:
            raise ValidationError("Inventory unit type must belong to the resolved tenant context.")
        if self.restriction_type in ['MIN_LOS', 'MAX_LOS']:
            if self.restriction_value is None:
                raise ValidationError(f"Restriction value is required for restriction type {self.restriction_type}.")
            if self.restriction_value < 1:
                raise ValidationError("Restriction value must be greater than or equal to 1 for LOS controls.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.inventory_unit_type.code if self.inventory_unit_type else "All Types"
        return f"{self.property.name} - {target} @ {self.date}: {self.restriction_type}"


class InventoryHold(BaseModel):
    HOLD_TYPE_CHOICES = (
        ('CART', 'Shopping Cart Hold'),
        ('GROUP_ALLOTMENT', 'Group Allotment'),
        ('PROMOTIONAL', 'Promotional Hold'),
    )
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('RELEASED', 'Released'),
        ('CONVERTED', 'Converted'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='holds')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='holds')
    inventory_unit_type = models.ForeignKey(InventoryUnitType, on_delete=models.CASCADE, related_name='holds')
    inventory_unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, null=True, blank=True, related_name='holds')
    
    hold_type = models.CharField(max_length=32, choices=HOLD_TYPE_CHOICES, default='CART')
    quantity = models.IntegerField(default=1)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='ACTIVE')

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Hold quantity must be greater than or equal to 1.")
        if not self.expires_at:
            raise ValidationError("Expiration timestamp is required.")
        if self.inventory_unit and self.inventory_unit.inventory_unit_type != self.inventory_unit_type:
            raise ValidationError("Target inventory unit type must match the specific inventory unit's type.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hold_type} Hold - {self.inventory_unit_type.code} (Qty: {self.quantity}, Status: {self.status})"
