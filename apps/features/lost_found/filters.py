import django_filters
from apps.features.lost_found.models import LostFoundItem

class LostFoundItemFilter(django_filters.FilterSet):
    property_id = django_filters.UUIDFilter(field_name='property_id')
    class Meta:
        model = LostFoundItem
        fields = ['property_id', 'item_type', 'status']
