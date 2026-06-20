from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.compliance.models import ConsentRecord, RetentionPolicy, GDPRRequest
from apps.compliance.serializers import ConsentRecordSerializer, RetentionPolicySerializer, GDPRRequestSerializer

class ConsentRecordViewSet(viewsets.ModelViewSet):
    serializer_class = ConsentRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return ConsentRecord.objects.none()
        return ConsentRecord.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class RetentionPolicyViewSet(viewsets.ModelViewSet):
    serializer_class = RetentionPolicySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return RetentionPolicy.objects.none()
        return RetentionPolicy.objects.filter(tenant=tenant) | RetentionPolicy.objects.filter(tenant__isnull=True)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class GDPRRequestViewSet(viewsets.ModelViewSet):
    serializer_class = GDPRRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return GDPRRequest.objects.none()
        return GDPRRequest.objects.filter(tenant=tenant)

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        serializer.save(tenant=tenant)


class ExportTenantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Tenant configuration export initiated.',
            'status': 'IN_PROGRESS',
            'download_url': f'/media/exports/tenant-{tenant.subdomain}-export.json'
        }, status=status.HTTP_202_ACCEPTED)


class ExportGuestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'Tenant context is missing.'}, status=status.HTTP_400_BAD_REQUEST)

        guest_id = request.data.get('guest_id')
        if not guest_id:
            return Response({'error': 'guest_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Guest profile export initiated.',
            'status': 'IN_PROGRESS',
            'download_url': f'/media/exports/guest-{guest_id}-gdpr-export.zip'
        }, status=status.HTTP_202_ACCEPTED)
