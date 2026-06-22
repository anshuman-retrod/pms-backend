from rest_framework import serializers
from apps.features.maintenance.models import MaintenanceTicket, MaintenanceSchedule

class MaintenanceTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceTicket
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise serializers.ValidationError("Property must belong to the resolved tenant context.")
        
        unit = data.get('inventory_unit')
        if unit and unit.property != prop:
            raise serializers.ValidationError("Inventory unit must belong to the target property.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceSchedule
        fields = '__all__'


class TicketAssignSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(required=True)
    user_id = serializers.UUIDField(required=True)


class TicketCompleteSerializer(serializers.Serializer):
    ticket_id = serializers.UUIDField(required=True)
