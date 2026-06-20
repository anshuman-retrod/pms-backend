from rest_framework import serializers
from apps.compliance.models import ConsentRecord, RetentionPolicy, GDPRRequest

class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = '__all__'
        read_only_fields = ['tenant']


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = '__all__'
        read_only_fields = ['tenant']


class GDPRRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GDPRRequest
        fields = '__all__'
        read_only_fields = ['tenant']
