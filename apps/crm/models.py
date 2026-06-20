import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import BaseModel
from apps.tenants.models import Tenant

class GuestProfile(BaseModel):
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('NON_BINARY', 'Non-Binary'),
    )
    GUEST_TYPE_CHOICES = (
        ('DOMESTIC', 'Domestic Guest'),
        ('FOREIGN', 'Foreign Guest'),
        ('CORPORATE', 'Corporate Client'),
        ('VIP', 'Very Important Person'),
    )
    LOYALTY_TIER_CHOICES = (
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
        ('BRONZE', 'Bronze'),
        ('STANDARD', 'Standard'),
    )

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='guest_profiles')
    master_guest = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='merged_profiles')
    
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=GENDER_CHOICES, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    
    guest_type = models.CharField(max_length=24, choices=GUEST_TYPE_CHOICES, default='DOMESTIC')
    loyalty_tier = models.CharField(max_length=24, choices=LOYALTY_TIER_CHOICES, default='STANDARD')
    loyalty_points = models.IntegerField(default=0)
    nps_score = models.IntegerField(null=True, blank=True)
    vip_notes = models.TextField(null=True, blank=True)
    
    email_opt_in = models.BooleanField(default=False)
    sms_opt_in = models.BooleanField(default=False)
    whatsapp_opt_in = models.BooleanField(default=False)
    
    total_stays = models.IntegerField(default=0)
    total_nights = models.IntegerField(default=0)
    last_stay_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(guest_type__in=['DOMESTIC', 'FOREIGN', 'CORPORATE', 'VIP']),
                name='guest_type_check'
            ),
            models.CheckConstraint(
                check=models.Q(loyalty_tier__in=['PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'STANDARD']),
                name='loyalty_tier_check'
            )
        ]

    def clean(self):
        if self.loyalty_points < 0:
            raise ValidationError("Loyalty points cannot be negative.")
        if self.total_stays < 0 or self.total_nights < 0:
            raise ValidationError("Stays and night counters cannot be negative.")
        if self.nps_score is not None and not (0 <= self.nps_score <= 10):
            raise ValidationError("NPS score must be between 0 and 10.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status_suffix = " (Merged/Inactive)" if not self.is_active else ""
        return f"{self.first_name} {self.last_name}{status_suffix}"


class GuestContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='guest_contacts')
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE, related_name='contacts')
    
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=32)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=16, null=True, blank=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'email', 'phone'], name='unique_tenant_email_phone'),
        ]

    def clean(self):
        if self.guest.tenant != self.tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} / {self.phone}"


class GuestDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ('PASSPORT', 'Passport'),
        ('NATIONAL_ID', 'National ID Card'),
        ('DRIVING_LICENCE', 'Driving Licence'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='guest_documents')
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE, related_name='documents')
    
    document_type = models.CharField(max_length=32, choices=DOCUMENT_TYPE_CHOICES)
    document_number = models.CharField(max_length=255)  # Reversible encrypted or signed representation
    expiry_date = models.DateField(null=True, blank=True)
    issuing_country = models.CharField(max_length=100, null=True, blank=True)
    attachment_url = models.CharField(max_length=2048, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(document_type__in=['PASSPORT', 'NATIONAL_ID', 'DRIVING_LICENCE']),
                name='document_type_check'
            ),
            models.UniqueConstraint(fields=['guest', 'document_type'], name='unique_guest_document_type'),
        ]

    def clean(self):
        if self.guest.tenant != self.tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.document_type} - {self.guest}"


class GuestPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='guest_preferences')
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE, related_name='preferences')
    
    preference_category = models.CharField(max_length=32, default='ROOM')
    preference_key = models.CharField(max_length=64)
    preference_value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['guest', 'preference_key'], name='unique_guest_preference_key'),
        ]

    def clean(self):
        if self.guest.tenant != self.tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.preference_key}: {self.preference_value}"


class GuestTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='guest_tags')
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'code'], name='unique_tenant_tag_code'),
        ]

    def __str__(self):
        scope = "Global" if not self.tenant else self.tenant.name
        return f"{self.name} ({scope})"


class GuestProfileTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE, related_name='profile_tags')
    tag = models.ForeignKey(GuestTag, on_delete=models.CASCADE, related_name='profile_tags')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['guest', 'tag'], name='unique_guest_tag_pair')
        ]

    def clean(self):
        if self.tag.tenant and self.tag.tenant != self.guest.tenant:
            raise ValidationError("Custom tags must belong to the same tenant as the guest profile.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guest} -> {self.tag.code}"


class ActivityQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Deletions are blocked on timeline records to preserve audit integrity.")

    def update(self, **kwargs):
        raise ValidationError("Updates are blocked on timeline records to preserve audit integrity.")


class ActivityManager(models.Manager):
    def get_queryset(self):
        return ActivityQuerySet(self.model, using=self._db)


class GuestActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='guest_activities')
    guest = models.ForeignKey(GuestProfile, on_delete=models.CASCADE, related_name='activities')
    
    timestamp = models.DateTimeField(default=timezone.now)
    activity_type = models.CharField(max_length=32)
    description = models.TextField()
    payload = models.JSONField(null=True, blank=True)

    objects = ActivityManager()

    def clean(self):
        if self.guest.tenant != self.tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Updates are blocked on timeline records to preserve audit integrity.")
        self.clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Deletions are blocked on timeline records to preserve audit integrity.")

    def __str__(self):
        return f"{self.activity_type} - {self.guest} @ {self.timestamp}"
