from celery import shared_task
from django.utils import timezone
from datetime import datetime, date, timedelta
from apps.features.rates.models import RatePlan, RateCalendar
from apps.features.rates.services import RateCalendarService, DerivedRateService, RatePlanService, RateCalculationService
from apps.core.tenants.models import Tenant, Property
from apps.features.inventory.models import InventoryUnitType
import logging

logger = logging.getLogger(__name__)

@shared_task(name="RateCalendarGenerationJob")
def rate_calendar_generation_job(tenant_id, property_id, start_date_str, end_date_str):
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        count = RateCalendarService.rebuild_calendar(tenant, property_id, start_date, end_date)
        logger.info(f"Generated {count} rate calendar entries for property {property_id} ({start_date} to {end_date}).")
        return count
    except Exception as e:
        logger.error(f"Error in RateCalendarGenerationJob: {e}")
        return 0

@shared_task(name="DerivedRateRecalculationJob")
def derived_rate_recalculation_job(tenant_id, property_id):
    """
    Cascades base rate updates by triggering a calendar rebuild for active derived rate plans.
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        
        count = RateCalendarService.rebuild_calendar(tenant, property_id, start_date, end_date)
        logger.info(f"Recalculated derived rates and updated {count} entries for property {property_id}.")
        return count
    except Exception as e:
        logger.error(f"Error in DerivedRateRecalculationJob: {e}")
        return 0

@shared_task(name="RateVersionSnapshotJob")
def rate_version_snapshot_job(rate_plan_id):
    try:
        rp = RatePlan.objects.get(id=rate_plan_id)
        version = RatePlanService.create_version_snapshot(rp)
        logger.info(f"Version snapshot created for rate plan {rp.code}: v{version.version_number}.")
        return str(version.id)
    except Exception as e:
        logger.error(f"Error in RateVersionSnapshotJob: {e}")
        return None

@shared_task(name="RateAuditJob")
def rate_audit_job(property_id=None):
    """
    Audits rate calendar for missing entries or 0-rate configurations over next 30 days.
    """
    issues = []
    start_date = date.today()
    end_date = start_date + timedelta(days=30)
    
    props = Property.objects.all()
    if property_id:
        props = props.filter(id=property_id)
        
    for prop in props:
        rate_plans = RatePlan.objects.filter(property=prop, is_active=True)
        unit_types = InventoryUnitType.objects.filter(property=prop)
        
        for rp in rate_plans:
            for ut in unit_types:
                curr_date = start_date
                while curr_date <= end_date:
                    cal = RateCalendar.objects.filter(
                        property=prop,
                        rate_plan=rp,
                        inventory_unit_type=ut,
                        date=curr_date
                    ).first()
                    
                    if not cal:
                        issues.append({
                            'property_id': str(prop.id),
                            'rate_plan_id': str(rp.id),
                            'unit_type_id': str(ut.id),
                            'date': str(curr_date),
                            'issue': 'Missing rate calendar entry'
                        })
                    elif cal.amount <= 0:
                        issues.append({
                            'property_id': str(prop.id),
                            'rate_plan_id': str(rp.id),
                            'unit_type_id': str(ut.id),
                            'date': str(curr_date),
                            'issue': 'Zero or negative rate amount'
                        })
                    curr_date += timedelta(days=1)
                    
    return issues
