from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from apps.core.common.models import BaseModel
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnit

class CleaningTask(BaseModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('PAUSED', 'Paused'),
        ('COMPLETED', 'Completed'),
    )
    PRIORITY_CHOICES = (
        ('ROUTINE', 'Routine'),
        ('RUSH', 'Rush'),
        ('VIP', 'VIP'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='cleaning_tasks')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='cleaning_tasks')
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cleaning_tasks'
    )
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=32, choices=PRIORITY_CHOICES, default='ROUTINE')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.status == 'COMPLETED':
            if self.room.housekeeping_status != 'clean':
                self.room.housekeeping_status = 'clean'
                self.room.save(update_fields=['housekeeping_status'])

    def __str__(self):
        return f"Cleaning {self.room.name} ({self.status})"


class RoomInspection(BaseModel):
    RESULT_CHOICES = (
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('REINSPECT', 'Reinspect'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='room_inspections')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='inspections')
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inspections_performed'
    )
    checklist_responses = models.JSONField(default=dict)
    score = models.IntegerField(default=100)
    result = models.CharField(max_length=32, choices=RESULT_CHOICES, default='PASSED')
    notes = models.TextField(null=True, blank=True)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")
        if self.score < 0 or self.score > 100:
            raise ValidationError("Inspection score must be between 0 and 100.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspection {self.room.name} - Score: {self.score} ({self.result})"


class DeepCleaningSchedule(BaseModel):
    STATUS_CHOICES = (
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('OVERDUE', 'Overdue'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='deep_cleaning_schedules')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='deep_clean_schedules')
    scheduled_date = models.DateField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='SCHEDULED')
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deep Clean {self.room.name} on {self.scheduled_date}"


class TurndownService(BaseModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('REFUSED', 'Refused'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='turndown_services')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='turndown_services')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    completed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Turndown {self.room.name} ({self.status})"


class MinibarInventory(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='minibar_inventories')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='minibar_inventories')
    item_name = models.CharField(max_length=120)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative.")
        if self.price < 0:
            raise ValidationError("Price cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_name} x {self.quantity} in Room {self.room.name}"


class MinibarRefill(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='minibar_refills')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='minibar_refills')
    item_name = models.CharField(max_length=120)
    quantity_consumed = models.IntegerField(default=0)
    quantity_refilled = models.IntegerField(default=0)
    is_billed = models.BooleanField(default=False)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")
        if self.quantity_consumed < 0 or self.quantity_refilled < 0:
            raise ValidationError("Refill quantities cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Minibar Refill {self.item_name} in Room {self.room.name}"


class AmenityInventory(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='amenity_inventories')
    room = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name='amenity_inventories')
    amenity_name = models.CharField(max_length=120)
    quantity = models.IntegerField(default=0)

    def clean(self):
        if self.room.tenant != self.tenant:
            raise ValidationError("Room must belong to the resolved tenant context.")
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Amenity {self.amenity_name} x {self.quantity} in Room {self.room.name}"


class HousekeepingInventory(BaseModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='housekeeping_inventories')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='housekeeping_inventories')
    supply_name = models.CharField(max_length=120)
    total_qty = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)

    def clean(self):
        if self.property.tenant != self.tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")
        if self.total_qty < 0 or self.reorder_level < 0:
            raise ValidationError("Quantities cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Supply: {self.supply_name} (Qty: {self.total_qty})"
