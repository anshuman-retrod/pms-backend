from rest_framework import viewsets, permissions, serializers
from apps.properties.models import PropertyConfiguration, PropertyContact
from apps.properties.serializers import PropertyConfigurationSerializer, PropertyContactSerializer

class PropertyConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return PropertyConfiguration.objects.none()
        return PropertyConfiguration.objects.filter(property__tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        prop = serializer.validated_data.get('property')
        if tenant and prop and prop.tenant != tenant:
            raise serializers.ValidationError("Property does not belong to this tenant.")
        serializer.save()


class PropertyContactViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return PropertyContact.objects.none()
        return PropertyContact.objects.filter(property__tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        prop = serializer.validated_data.get('property')
        if tenant and prop and prop.tenant != tenant:
            raise serializers.ValidationError("Property does not belong to this tenant.")
        serializer.save()
