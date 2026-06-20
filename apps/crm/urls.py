from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.crm.views import (
    GuestProfileViewSet, GuestContactViewSet, GuestDocumentViewSet,
    GuestPreferenceViewSet, GuestTagViewSet, GuestProfileTagViewSet,
    GuestActivityViewSet
)

router = DefaultRouter()
router.register(r'guests', GuestProfileViewSet, basename='guest')
router.register(r'contacts', GuestContactViewSet, basename='contact')
router.register(r'documents', GuestDocumentViewSet, basename='document')
router.register(r'preferences', GuestPreferenceViewSet, basename='preference')
router.register(r'tags', GuestTagViewSet, basename='tag')
router.register(r'profile-tags', GuestProfileTagViewSet, basename='profiletag')
router.register(r'activities', GuestActivityViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
]
