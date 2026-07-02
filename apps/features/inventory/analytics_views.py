from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from apps.features.inventory.models import InventoryUnitCategory, InventoryUnitType, InventoryUnit
from apps.features.assets.models import Asset
from apps.features.maintenance.models import MaintenanceTicket
from apps.features.availability.models import InventoryAvailability
from apps.features.linen.models import LinenItem

class InventoryAnalyticsSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        categories_count = InventoryUnitCategory.objects.filter(tenant=tenant).count()
        
        types_qs = InventoryUnitType.objects.filter(tenant=tenant)
        units_qs = InventoryUnit.objects.filter(tenant=tenant)
        
        if property_id:
            types_qs = types_qs.filter(property_id=property_id)
            units_qs = units_qs.filter(property_id=property_id)
            
        types_count = types_qs.count()
        units_count = units_qs.count()
        
        operational_count = units_qs.filter(operational_status='operational').count()
        maintenance_count = units_qs.filter(operational_status='maintenance').count()
        offline_count = units_qs.filter(operational_status='offline').count()
        
        return Response({
            'total_categories': categories_count,
            'total_unit_types': types_count,
            'total_units': units_count,
            'operational_status': {
                'operational': operational_count,
                'maintenance': maintenance_count,
                'offline': offline_count
            }
        }, status=status.HTTP_200_OK)


class InventoryAnalyticsAvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        avail_qs = InventoryAvailability.objects.filter(tenant=tenant)
        if property_id:
            avail_qs = avail_qs.filter(property_id=property_id)
            
        # Group by date or just summarize current stats
        total_allocated = avail_qs.aggregate(total=Sum('allocated_count'))['total'] or 0
        total_sold = avail_qs.aggregate(total=Sum('sold_count'))['total'] or 0
        total_blocked = avail_qs.aggregate(total=Sum('blocked_count'))['total'] or 0
        
        occupancy_rate = 0.0
        if total_allocated > 0:
            occupancy_rate = round((total_sold / total_allocated) * 100, 2)
            
        return Response({
            'total_allocated': total_allocated,
            'total_sold': total_sold,
            'total_blocked': total_blocked,
            'occupancy_rate_percentage': occupancy_rate
        }, status=status.HTTP_200_OK)


class InventoryAnalyticsAssetsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        assets_qs = Asset.objects.filter(tenant=tenant)
        if property_id:
            assets_qs = assets_qs.filter(property_id=property_id)
            
        total_assets = assets_qs.count()
        active_assets = assets_qs.filter(status='ACTIVE').count()
        maintenance_assets = assets_qs.filter(status='MAINTENANCE').count()
        decommissioned_assets = assets_qs.filter(status='DECOMMISSIONED').count()
        
        return Response({
            'total_assets': total_assets,
            'status_distribution': {
                'active': active_assets,
                'maintenance': maintenance_assets,
                'decommissioned': decommissioned_assets
            }
        }, status=status.HTTP_200_OK)


class InventoryAnalyticsMaintenanceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        tickets_qs = MaintenanceTicket.objects.filter(tenant=tenant)
        if property_id:
            tickets_qs = tickets_qs.filter(property_id=property_id)
            
        total_tickets = tickets_qs.count()
        open_tickets = tickets_qs.filter(status='OPEN').count()
        assigned_tickets = tickets_qs.filter(status='ASSIGNED').count()
        progress_tickets = tickets_qs.filter(status='IN_PROGRESS').count()
        completed_tickets = tickets_qs.filter(status='COMPLETED').count()
        cancelled_tickets = tickets_qs.filter(status='CANCELLED').count()
        
        priority_high_urgent = tickets_qs.filter(priority__in=['HIGH', 'URGENT']).count()
        
        return Response({
            'total_tickets': total_tickets,
            'status_distribution': {
                'open': open_tickets,
                'assigned': assigned_tickets,
                'in_progress': progress_tickets,
                'completed': completed_tickets,
                'cancelled': cancelled_tickets
            },
            'high_priority_count': priority_high_urgent
        }, status=status.HTTP_200_OK)


class InventoryAnalyticsOccupancyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        types_qs = InventoryUnitType.objects.filter(tenant=tenant)
        if property_id:
            types_qs = types_qs.filter(property_id=property_id)
            
        avg_base_occupancy = types_qs.aggregate(avg=Avg('base_occupancy'))['avg'] or 0.0
        avg_max_occupancy = types_qs.aggregate(avg=Avg('max_occupancy'))['avg'] or 0.0
        
        return Response({
            'average_base_occupancy': round(avg_base_occupancy, 2),
            'average_max_occupancy': round(avg_max_occupancy, 2)
        }, status=status.HTTP_200_OK)


class InventoryAnalyticsReportsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
            
        property_id = request.query_params.get('property_id') or request.query_params.get('property')
        
        # Linen low stock warning
        linen_qs = LinenItem.objects.filter(tenant=tenant)
        if property_id:
            linen_qs = linen_qs.filter(property_id=property_id)
            
        low_stock_linens = linen_qs.filter(total_qty__lt=F('par_stock')).values('name', 'code', 'total_qty', 'par_stock')
        
        # Out of order units
        units_qs = InventoryUnit.objects.filter(tenant=tenant, operational_status__in=['maintenance', 'offline'])
        if property_id:
            units_qs = units_qs.filter(property_id=property_id)
            
        ooo_units = units_qs.values('name', 'operational_status', 'housekeeping_status')
        
        return Response({
            'low_stock_linens': list(low_stock_linens),
            'out_of_order_units': list(ooo_units)
        }, status=status.HTTP_200_OK)
