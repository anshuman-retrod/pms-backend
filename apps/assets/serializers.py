from rest_framework import serializers
from apps.assets.models import Asset, AssetAssignment
from apps.inventory.models import InventoryUnit

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise serializers.ValidationError("Property must belong to the resolved tenant context.")
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    inventory_unit_name = serializers.CharField(source='inventory_unit.name', read_only=True)

    class Meta:
        model = AssetAssignment
        fields = '__all__'


class AssetAssignSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=True)
    inventory_unit_id = serializers.UUIDField(required=True)


class AssetTransferSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=True)
    new_inventory_unit_id = serializers.UUIDField(required=True)


class AssetUnassignSerializer(serializers.Serializer):
    asset_id = serializers.UUIDField(required=True)
