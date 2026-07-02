from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.inventory.views import (
    InventoryUnitCategoryViewSet, InventoryUnitTypeViewSet,
    InventoryUnitViewSet, InventoryRelationshipViewSet,
    AttributeDefinitionViewSet, InventoryUnitAttributeViewSet,
    AmenityViewSet, InventoryMediaViewSet
)
from apps.features.inventory.analytics_views import (
    InventoryAnalyticsSummaryView, InventoryAnalyticsAvailabilityView,
    InventoryAnalyticsAssetsView, InventoryAnalyticsMaintenanceView,
    InventoryAnalyticsOccupancyView, InventoryAnalyticsReportsView
)

router = DefaultRouter()
router.register(r'categories', InventoryUnitCategoryViewSet, basename='category')
router.register(r'types', InventoryUnitTypeViewSet, basename='type')
router.register(r'units', InventoryUnitViewSet, basename='unit')
router.register(r'relationships', InventoryRelationshipViewSet, basename='relationship')
router.register(r'attribute-definitions', AttributeDefinitionViewSet, basename='attributedefinition')
router.register(r'attributes', InventoryUnitAttributeViewSet, basename='attribute')
router.register(r'amenities', AmenityViewSet, basename='amenity')
router.register(r'media', InventoryMediaViewSet, basename='media')

urlpatterns = [
    path('', include(router.urls)),
    path('analytics/summary/', InventoryAnalyticsSummaryView.as_view(), name='inventory_analytics_summary'),
    path('analytics/availability/', InventoryAnalyticsAvailabilityView.as_view(), name='inventory_analytics_availability'),
    path('analytics/assets/', InventoryAnalyticsAssetsView.as_view(), name='inventory_analytics_assets'),
    path('analytics/maintenance/', InventoryAnalyticsMaintenanceView.as_view(), name='inventory_analytics_maintenance'),
    path('analytics/occupancy/', InventoryAnalyticsOccupancyView.as_view(), name='inventory_analytics_occupancy'),
    path('analytics/reports/', InventoryAnalyticsReportsView.as_view(), name='inventory_analytics_reports'),
]
