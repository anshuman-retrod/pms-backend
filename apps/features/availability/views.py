from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.features.availability.models import InventoryAvailability, InventoryRestriction, InventoryHold
from apps.features.availability.serializers import (
    InventoryAvailabilitySerializer,
    InventoryRestrictionSerializer,
    InventoryHoldSerializer,
    BulkAvailabilityUpdateSerializer
)
from apps.features.availability.permissions import HasAvailabilityPermission, IsRestrictionManager, IsHoldManager
from apps.features.availability.services import (
    AvailabilityCalendarService,
    HoldService
)
from django.utils import timezone

class InventoryAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryAvailabilitySerializer
    permission_classes = [HasAvailabilityPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return InventoryAvailability.objects.none()
        qs = InventoryAvailability.objects.filter(tenant=tenant)
        property_id = self.request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter('property_id', OpenApiTypes.UUID, required=True, description='Property ID context'),
            OpenApiParameter('start_date', OpenApiTypes.DATE, required=True, description='Start date (YYYY-MM-DD)'),
            OpenApiParameter('end_date', OpenApiTypes.DATE, required=True, description='End date (YYYY-MM-DD)'),
            OpenApiParameter('inventory_unit_type_id', OpenApiTypes.UUID, required=False, description='Optional Unit Type filter'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        property_id = request.query_params.get('property_id')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        unit_type_id = request.query_params.get('inventory_unit_type_id')

        if not property_id or not start_date_str or not end_date_str:
            return Response({'error': 'property_id, start_date, and end_date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if not start_date or not end_date:
            return Response({'error': 'Invalid date format.'}, status=status.HTTP_400_BAD_REQUEST)

        calendar_data = AvailabilityCalendarService.get_calendar(
            tenant=tenant,
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            unit_type_id=unit_type_id
        )
        return Response(calendar_data, status=status.HTTP_200_OK)

    @extend_schema(request=BulkAvailabilityUpdateSerializer)
    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BulkAvailabilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        property_id = serializer.validated_data['property_id']
        updates = serializer.validated_data['updates']

        created_count = 0
        updated_count = 0

        for item in updates:
            date = item['date']
            unit_type_id = item['inventory_unit_type_id']
            
            # Find or create
            avail, created = InventoryAvailability.objects.get_or_create(
                tenant=tenant,
                property_id=property_id,
                inventory_unit_type_id=unit_type_id,
                date=date,
                defaults={
                    'allocated_count': item.get('allocated_count', 0),
                    'sold_count': item.get('sold_count', 0),
                    'blocked_count': item.get('blocked_count', 0),
                    'overbooking_limit': item.get('overbooking_limit', 0),
                }
            )

            if not created:
                if 'allocated_count' in item:
                    avail.allocated_count = item['allocated_count']
                if 'sold_count' in item:
                    avail.sold_count = item['sold_count']
                if 'blocked_count' in item:
                    avail.blocked_count = item['blocked_count']
                if 'overbooking_limit' in item:
                    avail.overbooking_limit = item['overbooking_limit']
                avail.save()
                updated_count += 1
            else:
                created_count += 1

        return Response({
            'status': 'success',
            'created_records': created_count,
            'updated_records': updated_count
        }, status=status.HTTP_200_OK)


class InventoryRestrictionViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryRestrictionSerializer
    permission_classes = [IsRestrictionManager]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return InventoryRestriction.objects.none()
        qs = InventoryRestriction.objects.filter(tenant=tenant)
        property_id = self.request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs


class InventoryHoldViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryHoldSerializer
    permission_classes = [IsHoldManager]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return InventoryHold.objects.none()
        qs = InventoryHold.objects.filter(tenant=tenant)
        property_id = self.request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    @action(detail=True, methods=['patch'], url_path='release')
    def release(self, request, pk=None):
        hold = self.get_object()
        HoldService.release_hold(hold)
        serializer = self.get_serializer(hold)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='convert')
    def convert(self, request, pk=None):
        hold = self.get_object()
        HoldService.convert_hold(hold)
        serializer = self.get_serializer(hold)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        qs = InventoryHold.objects.filter(
            tenant=tenant,
            status='ACTIVE',
            expires_at__gt=timezone.now()
        )
        property_id = request.query_params.get('property_id')
        if property_id:
            qs = qs.filter(property_id=property_id)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
