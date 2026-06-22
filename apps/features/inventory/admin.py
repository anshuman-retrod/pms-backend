from django.contrib import admin
from apps.features.inventory.models import (
    InventoryUnitCategory, InventoryUnitType, InventoryUnit,
    InventoryRelationship, AttributeDefinition, InventoryUnitAttribute,
    Amenity, InventoryUnitTypeAmenity, InventoryMedia,
    Building, Floor, FloorPlan
)

@admin.register(InventoryUnitCategory)
class InventoryUnitCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'tenant', 'is_system', 'is_active', 'created_at')
    list_filter = ('is_system', 'is_active', 'tenant')
    search_fields = ('code', 'name')


@admin.register(InventoryUnitType)
class InventoryUnitTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'property', 'category', 'base_occupancy', 'max_occupancy', 'is_sellable')
    list_filter = ('property', 'category', 'is_sellable')
    search_fields = ('code', 'name')


class ChildUnitInline(admin.TabularInline):
    model = InventoryUnit
    fk_name = 'parent_unit'
    extra = 0
    raw_id_fields = ('inventory_unit_type',)


@admin.register(InventoryUnit)
class InventoryUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'inventory_unit_type', 'property', 'floor', 'operational_status', 'housekeeping_status', 'maintenance_status')
    list_filter = ('property', 'operational_status', 'housekeeping_status', 'maintenance_status', 'inventory_unit_type')
    search_fields = ('name', 'floor')
    raw_id_fields = ('parent_unit', 'inventory_unit_type')
    inlines = [ChildUnitInline]


@admin.register(InventoryRelationship)
class InventoryRelationshipAdmin(admin.ModelAdmin):
    list_display = ('parent_unit', 'child_unit', 'relation_type', 'tenant')
    list_filter = ('relation_type', 'tenant')
    raw_id_fields = ('parent_unit', 'child_unit')


@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ('code', 'data_type', 'tenant', 'created_at')
    list_filter = ('data_type', 'tenant')
    search_fields = ('code',)


@admin.register(InventoryUnitAttribute)
class InventoryUnitAttributeAdmin(admin.ModelAdmin):
    list_display = ('attribute_definition', 'value', 'inventory_unit_type', 'inventory_unit', 'tenant')
    list_filter = ('attribute_definition', 'tenant')
    raw_id_fields = ('inventory_unit_type', 'inventory_unit', 'attribute_definition')


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'tenant')
    list_filter = ('category', 'tenant')
    search_fields = ('code', 'name')


@admin.register(InventoryUnitTypeAmenity)
class InventoryUnitTypeAmenityAdmin(admin.ModelAdmin):
    list_display = ('inventory_unit_type', 'amenity', 'tenant')
    list_filter = ('tenant',)
    raw_id_fields = ('inventory_unit_type', 'amenity')


@admin.register(InventoryMedia)
class InventoryMediaAdmin(admin.ModelAdmin):
    list_display = ('media_type', 'media_url', 'sort_order', 'inventory_unit_type', 'inventory_unit', 'tenant')
    list_filter = ('media_type', 'tenant')
    raw_id_fields = ('inventory_unit_type', 'inventory_unit')


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'property', 'tenant')
    list_filter = ('property', 'tenant')
    search_fields = ('code', 'name')


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('name', 'floor_number', 'building')
    list_filter = ('building',)
    search_fields = ('name',)


@admin.register(FloorPlan)
class FloorPlanAdmin(admin.ModelAdmin):
    list_display = ('floor', 'file_url', 'version')
    list_filter = ('floor__building',)

