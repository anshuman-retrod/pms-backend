from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.features.availability.models import InventoryAvailability, InventoryRestriction, InventoryHold
from apps.features.inventory.models import InventoryUnitType, InventoryUnit

class InventoryAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryAvailability
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")

        unit_type = data.get('inventory_unit_type')
        if unit_type and unit_type.property != prop:
            raise ValidationError("Inventory unit type must belong to the target property.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class BulkAvailabilityItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    inventory_unit_type_id = serializers.UUIDField()
    allocated_count = serializers.IntegerField(min_value=0, required=False)
    sold_count = serializers.IntegerField(min_value=0, required=False)
    blocked_count = serializers.IntegerField(min_value=0, required=False)
    overbooking_limit = serializers.IntegerField(min_value=0, required=False)


class BulkAvailabilityUpdateSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    updates = serializers.ListField(child=BulkAvailabilityItemSerializer())


class InventoryRestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryRestriction
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")

        unit_type = data.get('inventory_unit_type')
        if unit_type and unit_type.property != prop:
            raise ValidationError("Inventory unit type must belong to the target property.")

        restriction_type = data.get('restriction_type')
        restriction_value = data.get('restriction_value')

        if restriction_type in ['MIN_LOS', 'MAX_LOS']:
            if restriction_value is None:
                raise ValidationError({"restriction_value": f"Restriction value is required for restriction type {restriction_type}."})
            if restriction_value < 1:
                raise ValidationError({"restriction_value": "Restriction value must be greater than or equal to 1 for LOS controls."})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class InventoryHoldSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryHold
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")

        unit_type = data.get('inventory_unit_type')
        if unit_type and unit_type.property != prop:
            raise ValidationError("Inventory unit type must belong to the target property.")

        unit = data.get('inventory_unit')
        if unit:
            if unit.property != prop:
                raise ValidationError("Inventory unit must belong to the target property.")
            if unit.inventory_unit_type != unit_type:
                raise ValidationError("Target inventory unit type must match the specific inventory unit's type.")

        quantity = data.get('quantity', 1)
        if quantity < 1:
            raise ValidationError({"quantity": "Hold quantity must be greater than or equal to 1."})

        if not data.get('expires_at') and not self.instance:
            raise ValidationError({"expires_at": "Expiration timestamp is required."})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)
