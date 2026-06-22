from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.features.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)
from apps.features.crm.services import EncryptionHelper

class GuestProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestProfile
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'master_guest', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class GuestContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestContact
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        guest = data.get('guest')
        if guest and guest.tenant != tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class GuestDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestDocument
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'is_verified')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        guest = data.get('guest')
        if guest and guest.tenant != tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        
        # Encrypt document number
        doc_num = validated_data.get('document_number')
        if doc_num:
            validated_data['document_number'] = EncryptionHelper.encrypt(doc_num)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        doc_num = validated_data.get('document_number')
        if doc_num:
            validated_data['document_number'] = EncryptionHelper.encrypt(doc_num)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['document_number'] = EncryptionHelper.decrypt(instance.document_number)
        return ret


class GuestPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestPreference
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        guest = data.get('guest')
        if guest and guest.tenant != tenant:
            raise ValidationError("Guest must belong to the resolved tenant context.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class GuestTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestTag
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class GuestProfileTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestProfileTag
        fields = '__all__'
        read_only_fields = ('id',)

    def validate(self, data):
        guest = data.get('guest')
        tag = data.get('tag')
        
        if tag.tenant and tag.tenant != guest.tenant:
            raise ValidationError("Custom tags must belong to the same tenant as the guest profile.")

        return data


class GuestActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestActivity
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'timestamp')


class MergeProfilesRequestSerializer(serializers.Serializer):
    duplicate_guest_id = serializers.UUIDField()


class AddLoyaltyPointsSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=255)


class AssignTagRequestSerializer(serializers.Serializer):
    tag_code = serializers.CharField(max_length=32)
