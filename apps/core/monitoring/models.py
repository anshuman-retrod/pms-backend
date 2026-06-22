import uuid
from django.db import models

class SystemHealthSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_name = models.CharField(max_length=120)
    status = models.CharField(max_length=32) # HEALTHY, DEGRADED, UNHEALTHY
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_health_snapshot'

    def __str__(self):
        return f"{self.service_name} : {self.status} at {self.recorded_at}"


class SystemMetric(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_code = models.CharField(max_length=64, db_index=True) # API_CALLS, ACTIVE_USERS, FAILED_LOGINS, ACTIVE_RESERVATIONS
    metric_value = models.FloatField(default=0.0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_metric'

    def __str__(self):
        return f"{self.metric_code} = {self.metric_value} at {self.recorded_at}"
