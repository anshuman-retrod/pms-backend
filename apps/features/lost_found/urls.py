from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.lost_found.views import LostFoundItemViewSet

router = DefaultRouter()
router.register(r'items', LostFoundItemViewSet, basename='lostfounditem')

urlpatterns = [
    path('', include(router.urls)),
]
