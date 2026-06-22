from rest_framework import serializers
from apps.core.audit.models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = [f.name for f in AuditLog._meta.fields]
