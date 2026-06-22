from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.assets.views import (
    AssetViewSet, AssetAssignView, AssetTransferView, AssetUnassignView
)

router = DefaultRouter()
router.register(r'', AssetViewSet, basename='asset')

urlpatterns = [
    path('assign/', AssetAssignView.as_view(), name='asset-assign'),
    path('transfer/', AssetTransferView.as_view(), name='asset-transfer'),
    path('unassign/', AssetUnassignView.as_view(), name='asset-unassign'),
    path('', include(router.urls)),
]
