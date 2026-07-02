from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.features.linen.models import LinenItem, LinenAssignment, LaundryRecord
from apps.features.linen.serializers import LinenItemSerializer, LinenAssignmentSerializer, LaundryRecordSerializer
from django.utils import timezone

class LinenItemViewSet(viewsets.ModelViewSet):
    serializer_class = LinenItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LinenItem.objects.none()
        
        property_id = self.request.query_params.get('property_id') or self.request.query_params.get('property')
        qs = LinenItem.objects.filter(tenant=tenant)
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @action(detail=True, methods=['post'], url_path='adjust-stock')
    def adjust_stock(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        item = self.get_object()
        quantity = request.data.get('quantity')
        
        if quantity is None:
            return Response({'error': 'quantity field is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            qty_int = int(quantity)
        except ValueError:
            return Response({'error': 'quantity must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            
        item.total_qty += qty_int
        if item.total_qty < 0:
            return Response({'error': 'Resulting total quantity cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            
        item.save()
        return Response(LinenItemSerializer(item).data, status=status.HTTP_200_OK)


class LinenAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = LinenAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LinenAssignment.objects.none()
        return LinenAssignment.objects.filter(tenant=tenant)


class LaundryRecordViewSet(viewsets.ModelViewSet):
    serializer_class = LaundryRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LaundryRecord.objects.none()
            
        property_id = self.request.query_params.get('property_id') or self.request.query_params.get('property')
        qs = LaundryRecord.objects.filter(tenant=tenant)
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @action(detail=True, methods=['post'], url_path='receive-laundry')
    def receive_laundry(self, request, pk=None):
        record = self.get_object()
        quantity = request.data.get('quantity')
        is_lost = request.data.get('is_lost', False)
        
        if quantity is None:
            return Response({'error': 'quantity field is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            qty_int = int(quantity)
        except ValueError:
            return Response({'error': 'quantity must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if qty_int < 0:
            return Response({'error': 'quantity cannot be negative.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if record.quantity_returned + qty_int > record.quantity_sent:
            return Response({'error': 'Total returned quantity cannot exceed quantity sent.'}, status=status.HTTP_400_BAD_REQUEST)
            
        record.quantity_returned += qty_int
        if record.quantity_returned == record.quantity_sent:
            record.status = 'RETURNED'
        else:
            record.status = 'LOST' if is_lost else 'PARTIALLY_RETURNED'
            
        record.save()
        return Response(LaundryRecordSerializer(record).data, status=status.HTTP_200_OK)
