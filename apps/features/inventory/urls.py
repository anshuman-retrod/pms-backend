from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.inventory.views import (
    InventoryUnitCategoryViewSet, InventoryUnitTypeViewSet,
    InventoryUnitViewSet, InventoryRelationshipViewSet,
    AttributeDefinitionViewSet, InventoryUnitAttributeViewSet,
    AmenityViewSet, InventoryMediaViewSet
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
]
