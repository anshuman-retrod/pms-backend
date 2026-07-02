from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.features.linen.views import LinenItemViewSet, LinenAssignmentViewSet, LaundryRecordViewSet

router = DefaultRouter()
router.register(r'items', LinenItemViewSet, basename='linenitem')
router.register(r'assignments', LinenAssignmentViewSet, basename='linenassignment')
router.register(r'laundry', LaundryRecordViewSet, basename='laundryrecord')

urlpatterns = [
    path('', include(router.urls)),
]
