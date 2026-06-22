from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.db.models import Q

from apps.features.crm.models import (
    GuestProfile, GuestContact, GuestDocument, GuestPreference,
    GuestTag, GuestProfileTag, GuestActivity
)
from apps.features.crm.serializers import (
    GuestProfileSerializer, GuestContactSerializer, GuestDocumentSerializer,
    GuestPreferenceSerializer, GuestTagSerializer, GuestProfileTagSerializer,
    GuestActivitySerializer, MergeProfilesRequestSerializer,
    AddLoyaltyPointsSerializer, AssignTagRequestSerializer
)
from apps.features.crm.permissions import (
    HasGuestPermission, IsMergeManager, IsVerifyDocumentManager,
    IsLoyaltyManager, IsTagManager
)
from apps.features.crm.services import (
    GuestMergeService, LoyaltyService, DocumentVerificationService,
    GuestSearchEngine, TaggingService
)

class GuestProfileViewSet(viewsets.ModelViewSet):
    serializer_class = GuestProfileSerializer
    permission_classes = [HasGuestPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestProfile.objects.none()
        # Only list active profiles by default, but allow retrieve of master profiles
        return GuestProfile.objects.filter(tenant=tenant)

    @extend_schema(
        parameters=[
            OpenApiParameter('query', OpenApiTypes.STR, required=False, description='Search by name, email, or phone'),
            OpenApiParameter('tag', OpenApiTypes.STR, required=False, description='Filter by tag code'),
        ]
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)
        
        query = request.query_params.get('query')
        tag = request.query_params.get('tag')
        
        results = GuestSearchEngine.search_guests(tenant=tenant, query_str=query, tag_code=tag)
        page = self.paginate_queryset(results)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=MergeProfilesRequestSerializer)
    @action(detail=True, methods=['post'], url_path='merge', permission_classes=[IsMergeManager])
    def merge(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        master_profile = self.get_object()
        serializer = MergeProfilesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        duplicate_id = serializer.validated_data['duplicate_guest_id']
        try:
            duplicate_profile = GuestProfile.objects.get(id=duplicate_id, tenant=tenant)
        except GuestProfile.DoesNotExist:
            return Response({'error': f'Duplicate profile with ID {duplicate_id} not found.'}, status=status.HTTP_404_NOT_FOUND)

        merged = GuestMergeService.merge_profiles(tenant, master_profile, duplicate_profile, user=request.user)
        output_serializer = self.get_serializer(merged)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=AddLoyaltyPointsSerializer)
    @action(detail=True, methods=['post'], url_path='loyalty', permission_classes=[IsLoyaltyManager])
    def loyalty(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = self.get_object()
        serializer = AddLoyaltyPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        points = serializer.validated_data['points']
        reason = serializer.validated_data['reason']

        updated_profile = LoyaltyService.add_points(tenant, profile, points, reason, user=request.user)
        output_serializer = self.get_serializer(updated_profile)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=AssignTagRequestSerializer)
    @action(detail=True, methods=['post'], url_path='tag', permission_classes=[IsTagManager])
    def tag(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = self.get_object()
        serializer = AssignTagRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag_code = serializer.validated_data['tag_code']
        pt = TaggingService.assign_tag(tenant, profile, tag_code, user=request.user)
        
        profile_serializer = self.get_serializer(profile)
        return Response(profile_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='activities')
    def activities(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = self.get_object()
        # Check active profile redirection
        active_profile = GuestMergeService.resolve_profile(profile)

        qs = GuestActivity.objects.filter(tenant=tenant, guest=active_profile).order_by('-timestamp')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = GuestActivitySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = GuestActivitySerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GuestContactViewSet(viewsets.ModelViewSet):
    serializer_class = GuestContactSerializer
    permission_classes = [HasGuestPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestContact.objects.none()
        return GuestContact.objects.filter(tenant=tenant)


class GuestDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = GuestDocumentSerializer
    permission_classes = [HasGuestPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestDocument.objects.none()
        return GuestDocument.objects.filter(tenant=tenant)

    @action(detail=True, methods=['post'], url_path='verify', permission_classes=[IsVerifyDocumentManager])
    def verify(self, request, pk=None):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context missing.'}, status=status.HTTP_400_BAD_REQUEST)

        doc = self.get_object()
        verified_doc = DocumentVerificationService.verify_document(tenant, doc, user=request.user)
        serializer = self.get_serializer(verified_doc)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GuestPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = GuestPreferenceSerializer
    permission_classes = [HasGuestPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestPreference.objects.none()
        return GuestPreference.objects.filter(tenant=tenant)


class GuestTagViewSet(viewsets.ModelViewSet):
    serializer_class = GuestTagSerializer
    permission_classes = [IsTagManager]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestTag.objects.filter(tenant__isnull=True)
        return GuestTag.objects.filter(Q(tenant__isnull=True) | Q(tenant=tenant))


class GuestProfileTagViewSet(viewsets.ModelViewSet):
    serializer_class = GuestProfileTagSerializer
    permission_classes = [IsTagManager]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestProfileTag.objects.none()
        return GuestProfileTag.objects.filter(guest__tenant=tenant)


class GuestActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GuestActivitySerializer
    permission_classes = [HasGuestPermission]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GuestActivity.objects.none()
        return GuestActivity.objects.filter(tenant=tenant).order_by('-timestamp')
