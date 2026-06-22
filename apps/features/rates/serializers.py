from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from apps.features.rates.models import (
    MealPlan, CancellationPolicy, ChildPolicy, RatePlan,
    RatePlanInventoryType, RatePlanVersion, DerivedRateConfig,
    RateRuleOccupancy, RateRuleDayOfWeek, RateCalendar,
    PackageProduct, PackageProductRatePlan
)

class MealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealPlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class CancellationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationPolicy
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class ChildPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildPolicy
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class RatePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatePlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        prop = data.get('property')
        if prop and prop.tenant != tenant:
            raise ValidationError("Property must belong to the resolved tenant context.")

        cancel = data.get('cancellation_policy')
        if cancel and cancel.tenant != tenant:
            raise ValidationError("Cancellation policy must belong to the resolved tenant context.")

        child = data.get('child_policy')
        if child and child.tenant != tenant:
            raise ValidationError("Child policy must belong to the resolved tenant context.")

        meal = data.get('default_meal_plan')
        if meal and meal.tenant and meal.tenant != tenant:
            raise ValidationError("Meal plan must belong to the resolved tenant context or be a system default.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class RatePlanInventoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatePlanInventoryType
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        rp = data.get('rate_plan')
        if rp and rp.tenant != tenant:
            raise ValidationError("Rate plan must belong to the resolved tenant context.")

        ut = data.get('inventory_unit_type')
        if ut and ut.tenant != tenant:
            raise ValidationError("Inventory unit type must belong to the resolved tenant context.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class RatePlanVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatePlanVersion
        fields = '__all__'
        read_only_fields = ('id', 'snapshot', 'effective_from')


class DerivedRateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DerivedRateConfig
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        child = data.get('child_rate_plan')
        anchor = data.get('anchor_rate_plan')

        if child and anchor and child == anchor:
            raise ValidationError("Child rate plan cannot be anchored to itself.")

        if child and child.tenant != tenant:
            raise ValidationError("Child rate plan must belong to the resolved tenant context.")

        if anchor and anchor.tenant != tenant:
            raise ValidationError("Anchor rate plan must belong to the resolved tenant context.")

        if child and not child.is_derived:
            raise ValidationError("Child rate plan must have is_derived set to True.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class RateRuleOccupancySerializer(serializers.ModelSerializer):
    class Meta:
        model = RateRuleOccupancy
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        mapping = data.get('rate_plan_inventory_type')
        if mapping and mapping.tenant != tenant:
            raise ValidationError("Rate plan inventory type must belong to the resolved tenant context.")

        occ_from = data.get('occupancy_from')
        occ_to = data.get('occupancy_to')
        if occ_from is not None and occ_to is not None:
            if occ_from < 1 or occ_to < 1:
                raise ValidationError("Occupancy ranges must be greater than or equal to 1.")
            if occ_from > occ_to:
                raise ValidationError("Occupancy from cannot be greater than occupancy to.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class RateRuleDayOfWeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateRuleDayOfWeek
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        mapping = data.get('rate_plan_inventory_type')
        if mapping and mapping.tenant != tenant:
            raise ValidationError("Rate plan inventory type must belong to the resolved tenant context.")

        dow = data.get('day_of_week')
        if dow is not None and not (1 <= dow <= 7):
            raise ValidationError("Day of week must be between 1 (Sunday) and 7 (Saturday).")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class RateCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateCalendar
        fields = '__all__'
        read_only_fields = ('id',)

    def validate(self, data):
        prop = data.get('property')
        rp = data.get('rate_plan')
        ut = data.get('inventory_unit_type')

        if rp and rp.property != prop:
            raise ValidationError("Rate plan must belong to the target property.")
        if ut and ut.property != prop:
            raise ValidationError("Inventory unit type must belong to the target property.")

        return data


class PackageProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageProduct
        fields = '__all__'
        read_only_fields = ('id', 'tenant', 'created_at', 'updated_at', 'created_by', 'updated_by')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        validated_data['created_by'] = request.user if request and request.user.is_authenticated else None
        return super().create(validated_data)


class PackageProductRatePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageProductRatePlan
        fields = '__all__'
        read_only_fields = ('id', 'tenant')

    def validate(self, data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)

        rp = data.get('rate_plan')
        pp = data.get('package_product')

        if rp and rp.tenant != tenant:
            raise ValidationError("Rate plan must belong to the resolved tenant context.")
        if pp and pp.tenant != tenant:
            raise ValidationError("Package product must belong to the resolved tenant context.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        validated_data['tenant'] = tenant
        return super().create(validated_data)


class RebuildCalendarSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
