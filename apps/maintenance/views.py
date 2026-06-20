from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.maintenance.models import MaintenanceTicket, MaintenanceSchedule
from apps.accounts.models import AppUser
from apps.maintenance.serializers import (
    MaintenanceTicketSerializer, MaintenanceScheduleSerializer, 
    TicketAssignSerializer, TicketCompleteSerializer
)

class MaintenanceTicketViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceTicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return MaintenanceTicket.objects.none()
        
        property_id = self.request.query_params.get('property_id') or self.request.query_params.get('property')
        status_filter = self.request.query_params.get('status')
        qs = MaintenanceTicket.objects.filter(tenant=tenant)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class MaintenanceScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MaintenanceScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return MaintenanceSchedule.objects.none()
        return MaintenanceSchedule.objects.filter(asset__tenant=tenant)


class TicketAssignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticket_id = serializer.validated_data['ticket_id']
        user_id = serializer.validated_data['user_id']

        try:
            ticket = MaintenanceTicket.objects.get(id=ticket_id, tenant=tenant)
        except MaintenanceTicket.DoesNotExist:
            return Response({'error': 'Maintenance ticket not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = AppUser.objects.get(id=user_id, tenant=tenant)
        except AppUser.DoesNotExist:
            return Response({'error': 'User not found under this tenant.'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = 'ASSIGNED'
        ticket.assigned_to = user
        ticket.save()

        # Update InventoryUnit maintenance status to 'active'
        unit = ticket.inventory_unit
        unit.maintenance_status = 'active'
        unit.save(update_fields=['maintenance_status', 'updated_at'])

        return Response(MaintenanceTicketSerializer(ticket).data, status=status.HTTP_200_OK)


class TicketCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TicketCompleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ticket_id = serializer.validated_data['ticket_id']

        try:
            ticket = MaintenanceTicket.objects.get(id=ticket_id, tenant=tenant)
        except MaintenanceTicket.DoesNotExist:
            return Response({'error': 'Maintenance ticket not found.'}, status=status.HTTP_400_BAD_REQUEST)

        ticket.status = 'COMPLETED'
        ticket.save()

        # Set InventoryUnit maintenance status to 'none'
        unit = ticket.inventory_unit
        unit.maintenance_status = 'none'
        unit.save(update_fields=['maintenance_status', 'updated_at'])

        return Response(MaintenanceTicketSerializer(ticket).data, status=status.HTTP_200_OK)
