from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.utils import timezone

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

    @extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT},
        description="Bulk update rooms status and assign housekeeping staff"
    )
    @action(detail=False, methods=['post'], url_path='bulk-assign')
    def bulk_assign(self, request):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Response({"error": "Tenant context not found"}, status=status.HTTP_400_BAD_REQUEST)

        room_ids = request.data.get('room_ids', [])
        assigned_staff_id = request.data.get('assigned_staff')
        housekeeping_status = request.data.get('housekeeping_status')

        if not room_ids:
            return Response({"error": "room_ids is required"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.features.inventory.models import InventoryUnit

        updated_rooms = []
        created_tasks = []

        for room_id in room_ids:
            try:
                room = InventoryUnit.objects.get(id=room_id, tenant=tenant)
            except InventoryUnit.DoesNotExist:
                continue

            if housekeeping_status and housekeeping_status != "No change":
                room.housekeeping_status = housekeeping_status.lower()
                room.save(update_fields=['housekeeping_status'])
                updated_rooms.append(room.id)

            task = CleaningTask.objects.filter(
                room=room,
                tenant=tenant,
                status__in=['PENDING', 'IN_PROGRESS']
            ).order_by('-created_at').first()

            if assigned_staff_id and assigned_staff_id != "No change":
                if task:
                    task.assigned_staff_id = assigned_staff_id
                    if housekeeping_status == 'clean':
                        task.status = 'COMPLETED'
                        task.completed_at = timezone.now()
                    task.save()
                else:
                    task = CleaningTask.objects.create(
                        tenant=tenant,
                        room=room,
                        assigned_staff_id=assigned_staff_id,
                        status='PENDING' if housekeeping_status != 'clean' else 'COMPLETED',
                        completed_at=timezone.now() if housekeeping_status == 'clean' else None,
                        priority='ROUTINE'
                    )
                created_tasks.append(task.id)
            elif housekeeping_status == 'clean' and task:
                task.status = 'COMPLETED'
                task.completed_at = timezone.now()
                task.save()
                created_tasks.append(task.id)

        return Response({
            "message": f"Successfully updated {len(updated_rooms)} rooms and updated/created {len(created_tasks)} tasks.",
            "updated_rooms": updated_rooms,
            "created_tasks": created_tasks
        }, status=status.HTTP_200_OK)


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
