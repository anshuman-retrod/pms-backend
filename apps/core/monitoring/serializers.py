from rest_framework import serializers
from apps.core.monitoring.models import SystemHealthSnapshot, SystemMetric

class SystemHealthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemHealthSnapshot
        fields = '__all__'


class SystemMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMetric
        fields = '__all__'
