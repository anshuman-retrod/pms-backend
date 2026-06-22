import uuid
from django.db import models
from apps.core.tenants.models import Property

class PropertyConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='configuration')
    timezone = models.CharField(max_length=50, default='UTC')
    currency = models.CharField(max_length=3, default='USD')
    language = models.CharField(max_length=10, default='en')
    tax_profile = models.CharField(max_length=64, null=True, blank=True)
    fiscal_year_start = models.CharField(max_length=16, default='01-01')
    checkin_time = models.CharField(max_length=16, default='14:00')
    checkout_time = models.CharField(max_length=16, default='12:00')

    class Meta:
        db_table = 'property_configuration'

    def __str__(self):
        return f"Config - {self.property.name}"


class PropertyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='contact')
    phone = models.CharField(max_length=32)
    email = models.EmailField(max_length=255)
    website = models.URLField(max_length=255, null=True, blank=True)
    emergency_contact = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        db_table = 'property_contact'

    def __str__(self):
        return f"Contact - {self.property.name}"
