from celery import shared_task
from django.utils import timezone
from apps.availability.models import InventoryAvailability, InventoryHold
from apps.availability.services import HoldService, AvailabilityCalculationService, AvailabilitySyncService
from apps.tenants.models import Tenant
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@shared_task(name="ReleaseExpiredHoldsJob")
def release_expired_holds_job():
    """
    Runs every minute.
    Finds active holds that have expired and sets their status to RELEASED.
    """
    count = HoldService.expire_holds()
    logger.info(f"Released {count} expired holds.")
    return count

@shared_task(name="AvailabilityRebuildJob")
def availability_rebuild_job(tenant_id, property_id, start_date_str, end_date_str):
    """
    Recalculates availability matrix.
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        count = AvailabilitySyncService.rebuild_matrix(tenant, property_id, start_date, end_date)
        logger.info(f"Rebuilt matrix for tenant {tenant_id}, property {property_id} ({start_date} to {end_date}): {count} records.")
        return count
    except Exception as e:
        logger.error(f"Error rebuilding availability matrix: {e}")
        return 0

@shared_task(name="AvailabilityAuditJob")
def availability_audit_job(property_id=None):
    """
    Detects negative inventory situations.
    """
    negatives = []
    qs = InventoryAvailability.objects.all()
    if property_id:
        qs = qs.filter(property_id=property_id)
        
    for avail in qs:
        active_holds = AvailabilityCalculationService.get_active_holds_quantity(
            avail.tenant, avail.property_id, avail.inventory_unit_type_id, avail.date
        )
        total_capacity = avail.allocated_count + avail.overbooking_limit
        total_demand = avail.sold_count + avail.blocked_count + active_holds
        available = total_capacity - total_demand
        
        if available < 0:
            msg = f"Negative inventory alert: Property {avail.property_id}, Date {avail.date}, UnitType {avail.inventory_unit_type_id}. Capacity: {total_capacity}, Demand: {total_demand} (Available: {available})"
            logger.warning(msg)
            negatives.append({
                'property_id': str(avail.property_id),
                'date': str(avail.date),
                'unit_type_id': str(avail.inventory_unit_type_id),
                'available': available
            })
            
    return negatives
