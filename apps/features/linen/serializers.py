from rest_framework import serializers
from apps.features.linen.models import LinenItem, LinenAssignment, LaundryRecord
from apps.features.inventory.models import InventoryUnit

class LinenItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinenItem
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')

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
        user = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = user
        return super().create(validated_data)


class LinenAssignmentSerializer(serializers.ModelSerializer):
    linen_item_name = serializers.CharField(source='linen_item.name', read_only=True)
    inventory_unit_name = serializers.CharField(source='inventory_unit.name', read_only=True)

    class Meta:
        model = LinenAssignment
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        linen_item = data.get('linen_item')
        if linen_item and linen_item.tenant != tenant:
            raise serializers.ValidationError("Linen item must belong to the resolved tenant context.")
            
        unit = data.get('inventory_unit')
        if unit and unit.tenant != tenant:
            raise serializers.ValidationError("Inventory unit must belong to the resolved tenant context.")
            
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = user
        return super().create(validated_data)


class LaundryRecordSerializer(serializers.ModelSerializer):
    linen_item_name = serializers.CharField(source='linen_item.name', read_only=True)

    class Meta:
        model = LaundryRecord
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by', 'deleted_at')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        
        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise serializers.ValidationError("Property must belong to the resolved tenant context.")
            
        linen_item = data.get('linen_item')
        if linen_item and linen_item.tenant != tenant:
            raise serializers.ValidationError("Linen item must belong to the resolved tenant context.")
            
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        user = getattr(request, 'user', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = user
        return super().create(validated_data)
