from django.contrib import admin
from apps.features.assets.models import Asset, AssetAssignment

class AssetAssignmentInline(admin.TabularInline):
    model = AssetAssignment
    extra = 1

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('asset_code', 'asset_name', 'asset_type', 'status', 'property', 'tenant')
    list_filter = ('asset_type', 'status', 'property')
    search_fields = ('asset_code', 'asset_name')
    inlines = [AssetAssignmentInline]
