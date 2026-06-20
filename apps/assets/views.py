from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from apps.assets.models import Asset, AssetAssignment
from apps.inventory.models import InventoryUnit
from apps.assets.serializers import (
    AssetSerializer, AssetAssignmentSerializer, 
    AssetAssignSerializer, AssetTransferSerializer, AssetUnassignSerializer
)

class AssetViewSet(viewsets.ModelViewSet):
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return Asset.objects.none()
        
        # Optional filters
        property_id = self.request.query_params.get('property_id') or self.request.query_params.get('property')
        status_filter = self.request.query_params.get('status')
        qs = Asset.objects.filter(tenant=tenant)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class AssetAssignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssetAssignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        asset_id = serializer.validated_data['asset_id']
        inventory_unit_id = serializer.validated_data['inventory_unit_id']

        try:
            asset = Asset.objects.get(id=asset_id, tenant=tenant)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit = InventoryUnit.objects.get(id=inventory_unit_id, tenant=tenant)
        except InventoryUnit.DoesNotExist:
            return Response({'error': 'Inventory unit not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Close active assignment if any
        AssetAssignment.objects.filter(asset=asset, removed_at__isnull=True).update(removed_at=timezone.now())

        # Create new assignment
        assignment = AssetAssignment.objects.create(
            asset=asset,
            inventory_unit=unit
        )

        return Response(AssetAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class AssetTransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssetTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        asset_id = serializer.validated_data['asset_id']
        new_unit_id = serializer.validated_data['new_inventory_unit_id']

        try:
            asset = Asset.objects.get(id=asset_id, tenant=tenant)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit = InventoryUnit.objects.get(id=new_unit_id, tenant=tenant)
        except InventoryUnit.DoesNotExist:
            return Response({'error': 'Inventory unit not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Close active assignment
        AssetAssignment.objects.filter(asset=asset, removed_at__isnull=True).update(removed_at=timezone.now())

        # Create new assignment
        assignment = AssetAssignment.objects.create(
            asset=asset,
            inventory_unit=unit
        )

        return Response(AssetAssignmentSerializer(assignment).data, status=status.HTTP_200_OK)


class AssetUnassignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AssetUnassignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        asset_id = serializer.validated_data['asset_id']

        try:
            asset = Asset.objects.get(id=asset_id, tenant=tenant)
        except Asset.DoesNotExist:
            return Response({'error': 'Asset not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Unassign active assignment
        active_assignment = AssetAssignment.objects.filter(asset=asset, removed_at__isnull=True).first()
        if not active_assignment:
            return Response({'error': 'Asset is not assigned.'}, status=status.HTTP_400_BAD_REQUEST)

        active_assignment.removed_at = timezone.now()
        active_assignment.save()

        return Response({'message': 'Asset unassigned successfully.'}, status=status.HTTP_200_OK)
