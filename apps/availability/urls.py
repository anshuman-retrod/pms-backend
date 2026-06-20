from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.availability.views import (
    InventoryAvailabilityViewSet,
    InventoryRestrictionViewSet,
    InventoryHoldViewSet
)

router = DefaultRouter()
router.register(r'availability', InventoryAvailabilityViewSet, basename='availability')
router.register(r'restrictions', InventoryRestrictionViewSet, basename='restriction')
router.register(r'holds', InventoryHoldViewSet, basename='hold')

urlpatterns = [
    path('', include(router.urls)),
]
