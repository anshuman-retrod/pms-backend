from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reference.views import (
    CountryViewSet, NationalityViewSet, LanguageViewSet,
    CurrencyViewSet, DocumentTypeViewSet, ReservationSourceViewSet
)

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'nationalities', NationalityViewSet, basename='nationality')
router.register(r'languages', LanguageViewSet, basename='language')
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'document-types', DocumentTypeViewSet, basename='documenttype')
router.register(r'reservation-sources', ReservationSourceViewSet, basename='reservationsource')

urlpatterns = [
    path('', include(router.urls)),
]
