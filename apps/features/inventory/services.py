from django.core.exceptions import ValidationError
from apps.features.inventory.models import (
    InventoryUnitCategory, InventoryUnitType, InventoryUnit,
    InventoryRelationship, AttributeDefinition, InventoryUnitAttribute,
    Amenity, InventoryUnitTypeAmenity, InventoryMedia
)

class InventoryCategoryService:
    @staticmethod
    def create_category(tenant, code, name, is_system=False, is_active=True):
        if not tenant and not is_system:
            raise ValidationError("Non-system categories must be assigned to a tenant.")
        return InventoryUnitCategory.objects.create(
            tenant=tenant, code=code, name=name, is_system=is_system, is_active=is_active
        )


class InventoryTypeService:
    @staticmethod
    def create_unit_type(tenant, property, category, code, name, base_occupancy=2, max_occupancy=2, max_adults=2, max_children=0, max_infants=0, is_sellable=True):
        if property.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")
        if category.tenant and category.tenant != tenant:
            raise ValidationError("Category must belong to the resolved tenant context or be a system default.")
        
        return InventoryUnitType.objects.create(
            tenant=tenant, property=property, category=category, code=code, name=name,
            base_occupancy=base_occupancy, max_occupancy=max_occupancy,
            max_adults=max_adults, max_children=max_children, max_infants=max_infants,
            is_sellable=is_sellable
        )


class InventoryUnitService:
    @staticmethod
    def check_circular_parent(unit_id, parent_unit):
        if not parent_unit:
            return
        if unit_id and str(unit_id) == str(parent_unit.id):
            raise ValidationError("A unit cannot be its own parent.")
        
        visited = set()
        if unit_id:
            visited.add(str(unit_id))
            
        curr = parent_unit
        while curr:
            curr_id = str(curr.id)
            if curr_id in visited:
                raise ValidationError("Circular parent reference detected in unit hierarchy.")
            visited.add(curr_id)
            curr = curr.parent_unit

    @classmethod
    def create_unit(cls, tenant, property, inventory_unit_type, name, parent_unit=None, floor=None, operational_status='operational', housekeeping_status='clean', maintenance_status='none'):
        if property.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")
        if inventory_unit_type.property != property:
            raise ValidationError("Inventory unit type must belong to the target property.")
        if parent_unit:
            if parent_unit.property != property:
                raise ValidationError("Parent unit must belong to the same property.")
            cls.check_circular_parent(None, parent_unit)

        return InventoryUnit.objects.create(
            tenant=tenant, property=property, inventory_unit_type=inventory_unit_type,
            parent_unit=parent_unit, name=name, floor=floor,
            operational_status=operational_status, housekeeping_status=housekeeping_status,
            maintenance_status=maintenance_status
        )

    @classmethod
    def update_unit(cls, unit, **fields):
        parent_unit = fields.get('parent_unit', unit.parent_unit)
        if parent_unit:
            if parent_unit.property != unit.property:
                raise ValidationError("Parent unit must belong to the same property.")
            cls.check_circular_parent(unit.id, parent_unit)

        for k, v in fields.items():
            setattr(unit, k, v)
        unit.save()
        return unit


class InventoryRelationshipService:
    @staticmethod
    def validate_relationship(parent_unit, child_unit):
        if not parent_unit or not child_unit:
            return
        if parent_unit.id == child_unit.id:
            raise ValidationError("Self relationships are not allowed.")
        if parent_unit.property != child_unit.property:
            raise ValidationError("Units in relationship must belong to the same property.")
            
        visited = set()
        def is_ancestor(curr, target):
            if curr.id == target.id:
                return True
            curr_id = str(curr.id)
            if curr_id in visited:
                return False
            visited.add(curr_id)
            parent_relations = InventoryRelationship.objects.filter(child_unit=curr)
            for relation in parent_relations:
                if is_ancestor(relation.parent_unit, target):
                    return True
            return False
        
        if is_ancestor(parent_unit, child_unit):
            raise ValidationError("Circular relationship detected. The parent unit is already a descendant of the child unit.")

    @classmethod
    def create_relationship(cls, tenant, parent_unit, child_unit, relation_type='composition'):
        if parent_unit.tenant != tenant or child_unit.tenant != tenant:
            raise ValidationError("Units in relationship must belong to the resolved tenant context.")
        cls.validate_relationship(parent_unit, child_unit)
        
        return InventoryRelationship.objects.create(
            tenant=tenant, parent_unit=parent_unit, child_unit=child_unit, relation_type=relation_type
        )


class InventoryAttributeService:
    @staticmethod
    def validate_attribute_value(definition, value):
        if definition.data_type == 'boolean':
            if value.lower() not in ['true', 'false', '1', '0']:
                raise ValidationError(f"Invalid boolean value '{value}' for attribute '{definition.code}'.")
        elif definition.data_type == 'number':
            try:
                float(value)
            except ValueError:
                raise ValidationError(f"Invalid numeric value '{value}' for attribute '{definition.code}'.")
        elif definition.data_type == 'choice':
            allowed = definition.allowed_values
            if not allowed or not isinstance(allowed, list):
                raise ValidationError(f"Attribute definition '{definition.code}' of type choice must define allowed_values.")
            if value not in allowed:
                raise ValidationError(f"Value '{value}' is not one of the allowed values: {allowed} for attribute '{definition.code}'.")

    @classmethod
    def create_unit_attribute(cls, tenant, attribute_definition, value, inventory_unit_type=None, inventory_unit=None):
        if not inventory_unit_type and not inventory_unit:
            raise ValidationError("Must target either an inventory unit type or a specific inventory unit.")
        if inventory_unit_type and inventory_unit:
            raise ValidationError("Cannot target both an inventory unit type and a specific inventory unit.")
        if attribute_definition.tenant and attribute_definition.tenant != tenant:
            raise ValidationError("Attribute definition must belong to the resolved tenant context or be a system default.")
        
        if inventory_unit_type and inventory_unit_type.tenant != tenant:
            raise ValidationError("Target inventory unit type must belong to the resolved tenant context.")
        if inventory_unit and inventory_unit.tenant != tenant:
            raise ValidationError("Target inventory unit must belong to the resolved tenant context.")

        cls.validate_attribute_value(attribute_definition, value)

        return InventoryUnitAttribute.objects.create(
            tenant=tenant, attribute_definition=attribute_definition, value=value,
            inventory_unit_type=inventory_unit_type, inventory_unit=inventory_unit
        )


class AmenityService:
    @staticmethod
    def create_amenity(tenant, code, name, category):
        return Amenity.objects.create(tenant=tenant, code=code, name=name, category=category)

    @staticmethod
    def map_amenity_to_type(tenant, inventory_unit_type, amenity):
        if inventory_unit_type.tenant != tenant:
            raise ValidationError("Target unit type must belong to the resolved tenant context.")
        if amenity.tenant and amenity.tenant != tenant:
            raise ValidationError("Amenity must belong to the resolved tenant context or be a system default.")
        
        return InventoryUnitTypeAmenity.objects.get_or_create(
            tenant=tenant, inventory_unit_type=inventory_unit_type, amenity=amenity
        )


class InventoryMediaService:
    @classmethod
    def create_media(cls, tenant, media_url, media_type='image', sort_order=0, inventory_unit_type=None, inventory_unit=None):
        if not inventory_unit_type and not inventory_unit:
            raise ValidationError("Must target either an inventory unit type or a specific inventory unit.")
        if inventory_unit_type and inventory_unit:
            raise ValidationError("Cannot target both an inventory unit type and a specific inventory unit.")
        
        if inventory_unit_type and inventory_unit_type.tenant != tenant:
            raise ValidationError("Target inventory unit type must belong to the resolved tenant context.")
        if inventory_unit and inventory_unit.tenant != tenant:
            raise ValidationError("Target inventory unit must belong to the resolved tenant context.")

        return InventoryMedia.objects.create(
            tenant=tenant, media_url=media_url, media_type=media_type, sort_order=sort_order,
            inventory_unit_type=inventory_unit_type, inventory_unit=inventory_unit
        )


class InventoryTypeCloneService:
    @staticmethod
    def clone_inventory_type(source_inventory_type, target_name, target_code, clone_media=False):
        from django.db import transaction

        tenant = source_inventory_type.tenant
        amenities_count = 0
        attributes_count = 0
        media_count = 0

        with transaction.atomic():
            new_type = InventoryUnitType.objects.create(
                tenant=tenant,
                property=source_inventory_type.property,
                category=source_inventory_type.category,
                code=target_code,
                name=target_name,
                base_occupancy=source_inventory_type.base_occupancy,
                max_occupancy=source_inventory_type.max_occupancy,
                max_adults=source_inventory_type.max_adults,
                max_children=source_inventory_type.max_children,
                max_infants=source_inventory_type.max_infants,
                is_sellable=source_inventory_type.is_sellable
            )

            # Copy Amenity mappings
            amenities = InventoryUnitTypeAmenity.objects.filter(inventory_unit_type=source_inventory_type)
            for mapping in amenities:
                InventoryUnitTypeAmenity.objects.create(
                    tenant=tenant,
                    inventory_unit_type=new_type,
                    amenity=mapping.amenity
                )
                amenities_count += 1

            # Copy Attributes
            attrs = InventoryUnitAttribute.objects.filter(inventory_unit_type=source_inventory_type)
            for attr in attrs:
                InventoryUnitAttribute.objects.create(
                    tenant=tenant,
                    inventory_unit_type=new_type,
                    attribute_definition=attr.attribute_definition,
                    value=attr.value
                )
                attributes_count += 1

            # Copy Media if requested
            if clone_media:
                media = InventoryMedia.objects.filter(inventory_unit_type=source_inventory_type)
                for item in media:
                    InventoryMedia.objects.create(
                        tenant=tenant,
                        inventory_unit_type=new_type,
                        media_url=item.media_url,
                        media_type=item.media_type,
                        sort_order=item.sort_order
                    )
                    media_count += 1

            return new_type, amenities_count, attributes_count, media_count
