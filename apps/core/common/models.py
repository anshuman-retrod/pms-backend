import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

class BaseQuerySet(models.QuerySet):
    def delete(self):
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def active(self):
        return self.filter(deleted_at__isnull=True)

class BaseManager(models.Manager):
    def get_queryset(self):
        return BaseQuerySet(self.model, using=self._db).active()

    def all_with_deleted(self):
        return BaseQuerySet(self.model, using=self._db)

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        db_constraint=False  # Avoid circular db constraints if any
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        db_constraint=False
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at', 'updated_at'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class SystemTax(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='system_taxes')
    name = models.CharField(max_length=120)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=32, default="percentage")  # percentage or fixed
    status = models.CharField(max_length=32, default="active")  # active or inactive

    class Meta:
        db_table = 'system_taxes'

    def __str__(self):
        return f"{self.name} - {self.rate}%"


class SystemDocumentType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='system_document_types')
    name = models.CharField(max_length=120)
    required_checkin = models.BooleanField(default=False)
    expiry_required = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_document_types'

    def __str__(self):
        return self.name



class SystemCurrency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='system_currencies')
    code = models.CharField(max_length=16)  # e.g., USD, INR
    symbol = models.CharField(max_length=16)  # e.g., $, ₹
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    # Format Settings
    symbol_position = models.CharField(max_length=32, default="after")
    decimal_places = models.IntegerField(default=2)
    decimal_separator = models.CharField(max_length=8, default="dot")
    thousands_separator = models.CharField(max_length=8, default="comma")
    add_space = models.BooleanField(default=True)
    show_decimals = models.BooleanField(default=True)

    class Meta:
        db_table = 'system_currencies'

    def __str__(self):
        return f"{self.name} ({self.code})"


class SystemDateFormat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='system_date_formats')
    format = models.CharField(max_length=64)  # e.g., YYYY-MM-DD
    label = models.CharField(max_length=120)  # e.g., 2026-06-27
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_date_formats'

    def __str__(self):
        return self.label


class SystemTimeFormat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='system_time_formats')
    format = models.CharField(max_length=64)  # e.g., HH:mm
    label = models.CharField(max_length=120)  # e.g., 14:30
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_time_formats'

    def __str__(self):
        return self.label


class SystemLanguage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=64, unique=True)
    code = models.CharField(max_length=16, unique=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_languages'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='departments')
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=64)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = 'system_departments'
        unique_together = ('tenant', 'code')

    def __str__(self):
        return self.name


class Shift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE, null=True, blank=True, related_name='shifts')
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=64)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = 'system_shifts'
        unique_together = ('tenant', 'code')

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"
