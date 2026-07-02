from rest_framework import serializers
from apps.features.lost_found.models import LostFoundItem

class LostFoundItemSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source='reported_by.name', read_only=True)

    class Meta:
        model = LostFoundItem
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
