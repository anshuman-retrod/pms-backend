from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction
import uuid

from apps.core.subscriptions.models import (
    Product, SubscriptionPlan, SubscriptionEntitlement, TenantSubscription,
    ProductFeature, TenantProduct, TenantProductLicense, TenantProductEntitlement, TenantProductUsage
)
from apps.core.subscriptions.serializers import (
    ProductSerializer, SubscriptionPlanSerializer, 
    SubscriptionEntitlementSerializer, TenantSubscriptionSerializer,
    SubscriptionActionSerializer, ProductFeatureSerializer,
    TenantProductSerializer, TenantProductLicenseSerializer,
    TenantProductEntitlementSerializer, TenantProductUsageSerializer,
    SuperadminTenantSubscriptionSerializer
)
from apps.core.subscriptions.permissions import IsSuperUserOrReadOnly
from apps.core.subscriptions.services import (
    ProductAccessService, LicenseValidationService,
    EntitlementValidationService, UsageTrackingService
)

def sync_tenant_products(tenant, plan, start_date, end_date, subscription_id):
    TenantProduct.objects.filter(tenant=tenant).update(status='SUSPENDED')
    for pp in plan.plan_products.all():
        TenantProduct.objects.update_or_create(
            tenant=tenant,
            product=pp.product,
            defaults={
                'tenant_subscription_id': subscription_id,
                'activated_at': start_date,
                'expires_at': end_date,
                'status': 'ACTIVE'
            }
        )


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsSuperUserOrReadOnly]

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated])
    def features(self, request, pk=None):
        """
        GET /api/products/{id}/features/
        POST /api/products/{id}/features/
        """
        product = self.get_object()
        if request.method == 'GET':
            features = ProductFeature.objects.filter(product=product)
            serializer = ProductFeatureSerializer(features, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            data = request.data.copy()
            data['product'] = product.id
            serializer = ProductFeatureSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='assign', permission_classes=[permissions.IsAuthenticated])
    def assign(self, request):
        """
        POST /api/products/assign/
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id')
        tenant_subscription_id = request.data.get('tenant_subscription_id')
        expires_days = int(request.data.get('expires_days', 30))

        if not product_id:
            return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not tenant_subscription_id:
            # Check for active subscription
            active_sub = TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').first()
            if not active_sub:
                return Response({'error': 'No active Tenant Subscription found.'}, status=status.HTTP_400_BAD_REQUEST)
            tenant_subscription_id = active_sub.id
        else:
            try:
                active_sub = TenantSubscription.objects.get(id=tenant_subscription_id, tenant=tenant)
            except TenantSubscription.DoesNotExist:
                return Response({'error': 'Tenant Subscription not found.'}, status=status.HTTP_404_NOT_FOUND)

        activated_at = timezone.now()
        expires_at = activated_at + timezone.timedelta(days=expires_days)

        tenant_product, created = TenantProduct.objects.update_or_create(
            tenant=tenant,
            product=product,
            defaults={
                'tenant_subscription_id': tenant_subscription_id,
                'activated_at': activated_at,
                'expires_at': expires_at,
                'status': 'ACTIVE'
            }
        )

        return Response(TenantProductSerializer(tenant_product).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='remove', permission_classes=[permissions.IsAuthenticated])
    def remove(self, request):
        """
        POST /api/products/remove/
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant_product = TenantProduct.objects.get(tenant=tenant, product_id=product_id)
            tenant_product.status = 'SUSPENDED'
            tenant_product.save()
            # Also suspend associated licenses
            TenantProductLicense.objects.filter(tenant_product=tenant_product).update(status='SUSPENDED')
            return Response({'message': 'Product access suspended successfully.'}, status=status.HTTP_200_OK)
        except TenantProduct.DoesNotExist:
            return Response({'error': 'Product is not assigned to this tenant.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='tenant-products', permission_classes=[permissions.IsAuthenticated])
    def tenant_products(self, request):
        """
        GET /api/products/tenant-products/
        """
        tenant = getattr(request.user, 'tenant', getattr(request, 'tenant', None))
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        products = TenantProduct.objects.filter(tenant=tenant)
        serializer = TenantProductSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-products', permission_classes=[permissions.IsAuthenticated])
    def my_products(self, request):
        """
        GET /api/products/my-products/
        """
        tenant = getattr(request.user, 'tenant', getattr(request, 'tenant', None))
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        products = TenantProduct.objects.filter(tenant=tenant, status='ACTIVE', expires_at__gt=timezone.now())
        serializer = TenantProductSerializer(products, many=True)
        return Response(serializer.data)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsSuperUserOrReadOnly]


class SubscriptionEntitlementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SubscriptionEntitlement.objects.all()
    serializer_class = SubscriptionEntitlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        plan_id = self.request.query_params.get('plan_id')
        if plan_id:
            return SubscriptionEntitlement.objects.filter(plan_id=plan_id)
        return SubscriptionEntitlement.objects.all()


class SubscriptionAssignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubscriptionActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_id = serializer.validated_data['plan_id']
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found or inactive.'}, status=status.HTTP_400_BAD_REQUEST)

        TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').update(status='CANCELLED')

        start = timezone.now().date()
        duration = 365 if plan.billing_cycle.upper() == 'YEARLY' else 30
        end = start + timezone.timedelta(days=duration)

        sub = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            start_date=start,
            end_date=end,
            status='ACTIVE'
        )
        sync_tenant_products(tenant, plan, start, end, sub.id)

        return Response(TenantSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class SubscriptionUpgradeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubscriptionActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_id = serializer.validated_data['plan_id']
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found or inactive.'}, status=status.HTTP_400_BAD_REQUEST)

        TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').update(status='UPGRADED')

        start = timezone.now().date()
        duration = 365 if plan.billing_cycle.upper() == 'YEARLY' else 30
        end = start + timezone.timedelta(days=duration)

        sub = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            start_date=start,
            end_date=end,
            status='ACTIVE'
        )
        sync_tenant_products(tenant, plan, start, end, sub.id)

        return Response(TenantSubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class SubscriptionDowngradeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SubscriptionActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        plan_id = serializer.validated_data['plan_id']
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Plan not found or inactive.'}, status=status.HTTP_400_BAD_REQUEST)

        TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').update(status='DOWNGRADED')

        start = timezone.now().date()
        duration = 365 if plan.billing_cycle.upper() == 'YEARLY' else 30
        end = start + timezone.timedelta(days=duration)

        sub = TenantSubscription.objects.create(
            tenant=tenant,
            plan=plan,
            start_date=start,
            end_date=end,
            status='ACTIVE'
        )
        sync_tenant_products(tenant, plan, start, end, sub.id)

        return Response(TenantSubscriptionSerializer(sub).data, status=status.HTTP_200_OK)


class SubscriptionUsageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        active_sub = TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').first()
        if not active_sub:
            return Response({
                'active_plan': None,
                'entitlements': {}
            }, status=status.HTTP_200_OK)

        entitlements = SubscriptionEntitlement.objects.filter(plan=active_sub.plan)
        ent_data = {}
        for ent in entitlements:
            ent_data[ent.feature_code] = {
                'type': ent.limit_type,
                'value': ent.limit_value
            }

        return Response({
            'active_plan': active_sub.plan.name,
            'billing_cycle': active_sub.plan.billing_cycle,
            'start_date': active_sub.start_date,
            'end_date': active_sub.end_date,
            'entitlements': ent_data
        }, status=status.HTTP_200_OK)


class ProductFeatureViewSet(viewsets.ModelViewSet):
    queryset = ProductFeature.objects.all()
    serializer_class = ProductFeatureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request.user, 'tenant', getattr(self.request, 'tenant', None))
        if tenant:
            return ProductFeature.objects.filter(tenant=tenant) | ProductFeature.objects.filter(tenant__isnull=True)
        return ProductFeature.objects.all()


class LicenseViewSet(viewsets.ModelViewSet):
    queryset = TenantProductLicense.objects.all()
    serializer_class = TenantProductLicenseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return TenantProductLicense.objects.filter(tenant_product__tenant=tenant)
        return TenantProductLicense.objects.all()

    @action(detail=False, methods=['post'], url_path='create', permission_classes=[permissions.IsAuthenticated])
    def create_license(self, request):
        """
        POST /api/licenses/create/
        """
        tenant_product_id = request.data.get('tenant_product_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not tenant_product_id or not start_date or not end_date:
            return Response({'error': 'tenant_product_id, start_date, and end_date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant_product = TenantProduct.objects.get(id=tenant_product_id)
        except TenantProduct.DoesNotExist:
            return Response({'error': 'Tenant Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        license_key = f"LIC-{uuid.uuid4().hex[:16].upper()}"

        license_obj = TenantProductLicense.objects.create(
            tenant_product=tenant_product,
            license_key=license_key,
            start_date=start_date,
            end_date=end_date,
            status='ACTIVE',
            issued_by=request.user
        )

        return Response(TenantProductLicenseSerializer(license_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='suspend', permission_classes=[permissions.IsAuthenticated])
    def suspend(self, request):
        """
        POST /api/licenses/suspend/
        """
        license_key = request.data.get('license_key')
        if not license_key:
            return Response({'error': 'license_key is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            license_obj = TenantProductLicense.objects.get(license_key=license_key)
            license_obj.status = 'SUSPENDED'
            license_obj.save()
            return Response(TenantProductLicenseSerializer(license_obj).data, status=status.HTTP_200_OK)
        except TenantProductLicense.DoesNotExist:
            return Response({'error': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='reactivate', permission_classes=[permissions.IsAuthenticated])
    def reactivate(self, request):
        """
        POST /api/licenses/reactivate/
        """
        license_key = request.data.get('license_key')
        if not license_key:
            return Response({'error': 'license_key is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            license_obj = TenantProductLicense.objects.get(license_key=license_key)
            license_obj.status = 'ACTIVE'
            license_obj.save()
            return Response(TenantProductLicenseSerializer(license_obj).data, status=status.HTTP_200_OK)
        except TenantProductLicense.DoesNotExist:
            return Response({'error': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get', 'post'], url_path='validate', permission_classes=[permissions.IsAuthenticated])
    def validate_lic(self, request):
        """
        GET /api/licenses/validate/
        POST /api/licenses/validate/
        """
        license_key = request.query_params.get('license_key') or request.data.get('license_key')
        if not license_key:
            return Response({'error': 'license_key is required.'}, status=status.HTTP_400_BAD_REQUEST)

        is_valid = LicenseValidationService.validate_license(license_key)
        return Response({'valid': is_valid})


class EntitlementViewSet(viewsets.ModelViewSet):
    queryset = TenantProductEntitlement.objects.all()
    serializer_class = TenantProductEntitlementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return TenantProductEntitlement.objects.filter(tenant_product__tenant=tenant)
        return TenantProductEntitlement.objects.all()

    @action(detail=False, methods=['post'], url_path='validate', permission_classes=[permissions.IsAuthenticated])
    def validate_entitlement(self, request):
        """
        POST /api/entitlements/validate/
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        feature_code = request.data.get('feature_code')
        current_value = request.data.get('current_value')

        if not feature_code:
            return Response({'error': 'feature_code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if current_value is not None:
            is_valid = EntitlementValidationService.validate_limit(tenant, feature_code, current_value)
            return Response({'valid': is_valid, 'feature_code': feature_code})
        else:
            has_ent = EntitlementValidationService.has_entitlement(tenant, feature_code)
            return Response({'entitled': has_ent, 'feature_code': feature_code})


class UsageViewSet(viewsets.ModelViewSet):
    queryset = TenantProductUsage.objects.all()
    serializer_class = TenantProductUsageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return TenantProductUsage.objects.filter(tenant_product__tenant=tenant)
        return TenantProductUsage.objects.all()

    @action(detail=False, methods=['get'], url_path='summary', permission_classes=[permissions.IsAuthenticated])
    def summary(self, request):
        """
        GET /api/usage/summary/
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        summary_data = UsageTrackingService.get_usage_summary(tenant)
        return Response(summary_data)

    @action(detail=False, methods=['post'], url_path='recalculate', permission_classes=[permissions.IsAuthenticated])
    def recalculate(self, request):
        """
        POST /api/usage/recalculate/
        """
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        metrics = ['ROOMS_USED', 'ACTIVE_USERS', 'PROPERTIES_USED', 'ACTIVE_RESERVATIONS']
        results = {}
        for m in metrics:
            usage_obj = UsageTrackingService.recalculate_usage(tenant, m)
            if usage_obj:
                results[m] = {
                    'usage_value': usage_obj.usage_value,
                    'usage_limit': usage_obj.usage_limit,
                    'percentage_used': float(usage_obj.percentage_used)
                }

        return Response({'message': 'Recalculation completed successfully.', 'results': results}, status=status.HTTP_200_OK)


class TenantSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = TenantSubscription.objects.all()
    serializer_class = SuperadminTenantSubscriptionSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        if tenant_id:
            return TenantSubscription.objects.filter(tenant_id=tenant_id)
        return TenantSubscription.objects.all()

    def perform_create(self, serializer):
        tenant = serializer.validated_data['tenant']
        plan = serializer.validated_data['plan']
        start_date = serializer.validated_data.get('start_date') or timezone.now().date()
        if not serializer.validated_data.get('end_date'):
            duration = 365 if plan.billing_cycle.upper() == 'YEARLY' else 30
            end_date = start_date + timezone.timedelta(days=duration)
        else:
            end_date = serializer.validated_data.get('end_date')
        status = serializer.validated_data.get('status', 'ACTIVE')
        if status == 'ACTIVE':
            TenantSubscription.objects.filter(tenant=tenant, status='ACTIVE').update(status='CANCELLED')
        sub = serializer.save(start_date=start_date, end_date=end_date)
        if status == 'ACTIVE':
            sync_tenant_products(tenant, plan, start_date, end_date, sub.id)

