from rest_framework import serializers
from apps.features.properties.models import PropertyConfiguration, PropertyContact

class PropertyConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyConfiguration
        fields = '__all__'


class PropertyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyContact
        fields = '__all__'
