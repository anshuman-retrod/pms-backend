from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.availability.views import (
    InventoryAvailabilityViewSet,
    InventoryRestrictionViewSet,
    InventoryHoldViewSet,
    GroupBlockViewSet,
    GroupBlockAllocationViewSet,
    ChannelViewSet,
    ChannelAllocationViewSet,
    DynamicAvailabilityRuleViewSet,
    WaitlistEntryViewSet,
    InventorySharedPoolViewSet,
    InventorySharedPoolUnitTypeViewSet
)

router = DefaultRouter()
router.register(r'availability', InventoryAvailabilityViewSet, basename='availability')
router.register(r'restrictions', InventoryRestrictionViewSet, basename='restriction')
router.register(r'holds', InventoryHoldViewSet, basename='hold')
router.register(r'group-blocks', GroupBlockViewSet, basename='groupblock')
router.register(r'group-block-allocations', GroupBlockAllocationViewSet, basename='groupblockallocation')
router.register(r'channels', ChannelViewSet, basename='channel')
router.register(r'channel-allocations', ChannelAllocationViewSet, basename='channelallocation')
router.register(r'rules', DynamicAvailabilityRuleViewSet, basename='dynamicavailabilityrule')
router.register(r'waitlist', WaitlistEntryViewSet, basename='waitlistentry')
router.register(r'shared-pools', InventorySharedPoolViewSet, basename='sharedpool')
router.register(r'shared-pool-unit-types', InventorySharedPoolUnitTypeViewSet, basename='sharedpoolunittype')

urlpatterns = [
    path('', include(router.urls)),
]
