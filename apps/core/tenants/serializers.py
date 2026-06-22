from rest_framework import serializers
from apps.core.tenants.models import (
    Tenant, Property, TenantBranding, TenantDomain, 
    TenantConfiguration, TenantIsolationConfig
)

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'deleted_at', 'created_by', 'updated_by')


class TenantBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantBranding
        fields = '__all__'


class TenantDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantDomain
        fields = '__all__'


class TenantConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantConfiguration
        fields = '__all__'


class TenantIsolationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantIsolationConfig
        fields = '__all__'

