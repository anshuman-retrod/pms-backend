from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.features.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)
from apps.features.crm.services import EncryptionHelper

class GuestProfileSerializer(serializers.ModelSerializer):
    primary_email = serializers.SerializerMethodField()
    primary_phone = serializers.SerializerMethodField()
    primary_address = serializers.SerializerMethodField()
    id_type = serializers.SerializerMethodField()
    id_number = serializers.SerializerMethodField()
    id_proof_url = serializers.SerializerMethodField()

    class Meta:
        model = GuestProfile
        fields = (
            'id', 'tenant', 'master_guest', 'first_name', 'last_name', 'date_of_birth',
            'gender', 'nationality', 'preferred_language', 'guest_type', 'loyalty_tier',
            'loyalty_points', 'nps_score', 'vip_notes', 'email_opt_in', 'sms_opt_in',
            'whatsapp_opt_in', 'total_stays', 'total_nights', 'last_stay_date', 'is_active',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'primary_email',
            'primary_phone', 'primary_address', 'id_type', 'id_number', 'id_proof_url'
        )
        read_only_fields = ('id', 'tenant', 'master_guest', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def get_primary_email(self, obj):
        primary_contact = obj.contacts.filter(is_primary=True).first()
        return primary_contact.email if primary_contact else ""

    def get_primary_phone(self, obj):
        primary_contact = obj.contacts.filter(is_primary=True).first()
        return primary_contact.phone if primary_contact else ""

    def get_primary_address(self, obj):
        primary_contact = obj.contacts.filter(is_primary=True).first()
        if primary_contact:
            parts = [primary_contact.address_line_1, primary_contact.address_line_2, primary_contact.city, primary_contact.state, primary_contact.country]
            return ", ".join([p for p in parts if p])
        return ""

    def get_id_type(self, obj):
        primary_doc = obj.documents.first()
        return primary_doc.document_type if primary_doc else ""

    def get_id_proof_url(self, obj):
        primary_doc = obj.documents.first()
        return primary_doc.attachment_url if primary_doc else ""

    def get_id_number(self, obj):
        primary_doc = obj.documents.first()
        if primary_doc:
            return EncryptionHelper.decrypt(primary_doc.document_number)
        return ""

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
