from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from apps.features.housekeeping.models import (
    CleaningTask, RoomInspection, DeepCleaningSchedule,
    TurndownService, MinibarInventory, MinibarRefill,
    AmenityInventory, HousekeepingInventory
)
from apps.features.housekeeping.serializers import (
    CleaningTaskSerializer, RoomInspectionSerializer, DeepCleaningScheduleSerializer,
    TurndownServiceSerializer, MinibarInventorySerializer, MinibarRefillSerializer,
    AmenityInventorySerializer, HousekeepingInventorySerializer
)

class HousekeepingBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return self.queryset.model.objects.none()
        return self.queryset.model.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class CleaningTaskViewSet(HousekeepingBaseViewSet):
    queryset = CleaningTask.objects.all()
    serializer_class = CleaningTaskSerializer

    @extend_schema(
        request=CleaningTaskSerializer,
        responses={200: CleaningTaskSerializer},
        description="Assign a staff member to a cleaning task"
    )
    @action(detail=True, methods=['patch'], url_path='assign')
    def assign_staff(self, request, pk=None):
        task = self.get_object()
        assigned_staff_id = request.data.get('assigned_staff')
        
        if assigned_staff_id is not None:
            task.assigned_staff_id = assigned_staff_id
            task.save()
            return Response(CleaningTaskSerializer(task).data, status=status.HTTP_200_OK)
        return Response({"error": "assigned_staff field is required"}, status=status.HTTP_400_BAD_REQUEST)


class RoomInspectionViewSet(HousekeepingBaseViewSet):
    queryset = RoomInspection.objects.all()
    serializer_class = RoomInspectionSerializer


class DeepCleaningScheduleViewSet(HousekeepingBaseViewSet):
    queryset = DeepCleaningSchedule.objects.all()
    serializer_class = DeepCleaningScheduleSerializer


class TurndownServiceViewSet(HousekeepingBaseViewSet):
    queryset = TurndownService.objects.all()
    serializer_class = TurndownServiceSerializer


class MinibarInventoryViewSet(HousekeepingBaseViewSet):
    queryset = MinibarInventory.objects.all()
    serializer_class = MinibarInventorySerializer


class MinibarRefillViewSet(HousekeepingBaseViewSet):
    queryset = MinibarRefill.objects.all()
    serializer_class = MinibarRefillSerializer


class AmenityInventoryViewSet(HousekeepingBaseViewSet):
    queryset = AmenityInventory.objects.all()
    serializer_class = AmenityInventorySerializer


class HousekeepingInventoryViewSet(HousekeepingBaseViewSet):
    queryset = HousekeepingInventory.objects.all()
    serializer_class = HousekeepingInventorySerializer
