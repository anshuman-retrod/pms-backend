from django.db import models
from django.core.exceptions import ValidationError
from apps.core.common.models import BaseModel
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnit

class LinenItem(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='linen_items')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='linen_items')
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=64)
    total_qty = models.IntegerField(default=0)
    par_stock = models.IntegerField(default=0)
    status = models.CharField(max_length=32, choices=(('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')), default='ACTIVE')

    class Meta:
        db_table = 'linen_item'
        constraints = [
            models.UniqueConstraint(fields=['property', 'code'], name='unique_property_linen_code')
        ]

    def clean(self):
        if self.total_qty < 0:
            raise ValidationError("Total quantity cannot be negative.")
        if self.par_stock < 0:
            raise ValidationError("Par stock quantity cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


class LinenAssignment(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='linen_assignments')
    linen_item = models.ForeignKey(LinenItem, on_delete=models.CASCADE, related_name='assignments')
    inventory_unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='linen_assignments')
    quantity = models.IntegerField(default=1)

    class Meta:
        db_table = 'linen_assignment'

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Assigned quantity must be at least 1.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.linen_item.name} x {self.quantity} -> {self.inventory_unit.name}"


class LaundryRecord(BaseModel):
    STATUS_CHOICES = (
        ('SENT', 'Sent'),
        ('RETURNED', 'Returned'),
        ('PARTIALLY_RETURNED', 'Partially Returned'),
        ('LOST', 'Lost'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='laundry_records')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='laundry_records')
    linen_item = models.ForeignKey(LinenItem, on_delete=models.CASCADE, related_name='laundry_records')
    quantity_sent = models.IntegerField()
    quantity_returned = models.IntegerField(default=0)
    sent_date = models.DateField()
    expected_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='SENT')

    class Meta:
        db_table = 'laundry_record'

    def clean(self):
        if self.quantity_sent < 1:
            raise ValidationError("Quantity sent to laundry must be at least 1.")
        if self.quantity_returned < 0:
            raise ValidationError("Quantity returned cannot be negative.")
        if self.quantity_returned > self.quantity_sent:
            raise ValidationError("Quantity returned cannot exceed quantity sent.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.linen_item.name} - Sent: {self.quantity_sent}, Returned: {self.quantity_returned} ({self.status})"
