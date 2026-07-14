from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.housekeeping.views import (
    CleaningTaskViewSet, RoomInspectionViewSet, DeepCleaningScheduleViewSet,
    TurndownServiceViewSet, MinibarInventoryViewSet, MinibarRefillViewSet,
    AmenityInventoryViewSet, HousekeepingInventoryViewSet
)

router = DefaultRouter()
router.register(r'tasks', CleaningTaskViewSet, basename='cleaningtask')
router.register(r'inspections', RoomInspectionViewSet, basename='roominspection')
router.register(r'deep-cleaning', DeepCleaningScheduleViewSet, basename='deepcleaningschedule')
router.register(r'turndown', TurndownServiceViewSet, basename='turndownservice')
router.register(r'minibar-inventory', MinibarInventoryViewSet, basename='minibarinventory')
router.register(r'minibar-refills', MinibarRefillViewSet, basename='minibarrefill')
router.register(r'amenities', AmenityInventoryViewSet, basename='amenityinventory')
router.register(r'supplies', HousekeepingInventoryViewSet, basename='housekeepinginventory')

urlpatterns = [
    path('', include(router.urls)),
]
