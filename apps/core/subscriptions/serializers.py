from rest_framework import serializers
from apps.core.subscriptions.models import (
    Product, SubscriptionPlan, SubscriptionPlanProduct, SubscriptionEntitlement, TenantSubscription,
    ProductFeature, TenantProduct, TenantProductLicense, TenantProductEntitlement, TenantProductUsage
)

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class SubscriptionEntitlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionEntitlement
        fields = '__all__'


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    entitlements = SubscriptionEntitlementSerializer(many=True, read_only=True)
    products = ProductSerializer(many=True, read_only=True)
    product_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False,
        help_text="List of Product UUIDs to link to this plan"
    )

    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'billing_cycle', 'price', 'currency', 'is_active', 'products', 'product_ids', 'entitlements']

    def create(self, validated_data):
        product_ids = validated_data.pop('product_ids', [])
        plan = SubscriptionPlan.objects.create(**validated_data)
        for prod_id in product_ids:
            try:
                prod = Product.objects.get(id=prod_id)
                SubscriptionPlanProduct.objects.create(plan=plan, product=prod)
            except Product.DoesNotExist:
                pass
        return plan


class TenantSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = TenantSubscription
        fields = ['id', 'tenant', 'plan', 'plan_name', 'start_date', 'end_date', 'status']
        read_only_fields = ['tenant']


class SubscriptionActionSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField(required=True)


class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = '__all__'


class TenantProductSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source='product.code', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = TenantProduct
        fields = '__all__'


class TenantProductLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantProductLicense
        fields = '__all__'


class TenantProductEntitlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantProductEntitlement
        fields = '__all__'


class TenantProductUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantProductUsage
        fields = '__all__'

