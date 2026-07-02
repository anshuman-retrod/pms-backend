from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.features.lost_found.models import LostFoundItem
from apps.features.lost_found.serializers import LostFoundItemSerializer
from django.utils import timezone

class LostFoundItemViewSet(viewsets.ModelViewSet):
    serializer_class = LostFoundItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return LostFoundItem.objects.none()
            
        property_id = self.request.query_params.get('property_id') or self.request.query_params.get('property')
        item_type = self.request.query_params.get('item_type')
        status_filter = self.request.query_params.get('status')
        
        qs = LostFoundItem.objects.filter(tenant=tenant)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if item_type:
            qs = qs.filter(item_type=item_type)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=['post'], url_path='claim')
    def claim_item(self, request, pk=None):
        item = self.get_object()
        claimed_by = request.data.get('claimed_by')
        
        if not claimed_by:
            return Response({'error': 'claimed_by field is required to claim an item.'}, status=status.HTTP_400_BAD_REQUEST)
            
        item.status = 'CLAIMED'
        item.claimed_by = claimed_by
        item.claimed_date = timezone.now()
        item.save()
        return Response(LostFoundItemSerializer(item).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='dispose')
    def dispose_item(self, request, pk=None):
        item = self.get_object()
        reason = request.data.get('disposed_reason')
        
        if not reason:
            return Response({'error': 'disposed_reason field is required to dispose an item.'}, status=status.HTTP_400_BAD_REQUEST)
            
        item.status = 'DISPOSED'
        item.disposed_reason = reason
        item.save()
        return Response(LostFoundItemSerializer(item).data, status=status.HTTP_200_OK)
