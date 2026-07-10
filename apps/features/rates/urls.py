from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.rates.views import (
    MealPlanViewSet, CancellationPolicyViewSet, ChildPolicyViewSet,
    RatePlanViewSet, RatePlanInventoryTypeViewSet, RatePlanVersionViewSet,
    DerivedRateConfigViewSet, RateRuleOccupancyViewSet, RateRuleDayOfWeekViewSet,
    RateCalendarViewSet, TenantMealPlanPriceViewSet,
    HospitalityPackageViewSet, ServiceCategoryViewSet, ServiceViewSet, CouponViewSet
)

router = DefaultRouter()
router.register(r'tenant-meal-plan-prices', TenantMealPlanPriceViewSet, basename='tenantmealplanprice')
router.register(r'meal-plans', MealPlanViewSet, basename='mealplan')
router.register(r'cancellation-policies', CancellationPolicyViewSet, basename='cancellationpolicy')
router.register(r'child-policies', ChildPolicyViewSet, basename='childpolicy')
router.register(r'rate-plans', RatePlanViewSet, basename='rateplan')
router.register(r'rate-plan-inventories', RatePlanInventoryTypeViewSet, basename='rateplaninventory')
router.register(r'rate-plan-versions', RatePlanVersionViewSet, basename='rateplanversion')
router.register(r'derived-rates', DerivedRateConfigViewSet, basename='derivedrate')
router.register(r'occupancy-rules', RateRuleOccupancyViewSet, basename='occupancyrule')
router.register(r'day-rules', RateRuleDayOfWeekViewSet, basename='dayrule')
router.register(r'calendar', RateCalendarViewSet, basename='ratecalendar')
router.register(r'packages', HospitalityPackageViewSet, basename='hospitalitypackage')
router.register(r'service-categories', ServiceCategoryViewSet, basename='servicecategory')
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = [
    path('', include(router.urls)),
]
