from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reservations.views import (
    CorporateAccountViewSet, GroupBlockViewSet, ReservationViewSet
)

router = DefaultRouter()
router.register(r'corporate-accounts', CorporateAccountViewSet, basename='corporateaccount')
router.register(r'group-blocks', GroupBlockViewSet, basename='groupblock')
router.register(r'bookings', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
]
