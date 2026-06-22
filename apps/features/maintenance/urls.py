from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.maintenance.views import (
    MaintenanceTicketViewSet, MaintenanceScheduleViewSet, 
    TicketAssignView, TicketCompleteView
)

router = DefaultRouter()
router.register(r'tickets', MaintenanceTicketViewSet, basename='ticket')
router.register(r'schedules', MaintenanceScheduleViewSet, basename='schedule')

urlpatterns = [
    path('assign/', TicketAssignView.as_view(), name='ticket-assign'),
    path('complete/', TicketCompleteView.as_view(), name='ticket-complete'),
    path('', include(router.urls)),
]
