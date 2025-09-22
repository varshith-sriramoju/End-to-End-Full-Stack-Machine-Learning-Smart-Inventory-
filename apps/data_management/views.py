from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from celery.result import AsyncResult
from .models import SalesData, DataUpload, DataValidationError, DataQualityReport
from .serializers import (
    SalesDataSerializer, DataUploadSerializer, 
    DataValidationErrorSerializer, DataQualityReportSerializer,
    DataUploadCreateSerializer
)
from .tasks import process_data_upload
import logging

logger = logging.getLogger(__name__)

class SalesDataListView(generics.ListAPIView):
    """List sales data with filtering and pagination"""
    queryset = SalesData.objects.all()
    serializer_class = SalesDataSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['store__store_id', 'product__sku_id', 'date', 'promotions_flag']
    search_fields = ['store__store_id', 'product__sku_id', 'product__name']
    ordering_fields = ['date', 'sales', 'price']
    ordering = ['-date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user's accessible stores if not admin
        user_profile = getattr(self.request.user, 'userprofile', None)
        if user_profile and user_profile.role != 'admin':
            accessible_stores = user_profile.stores.all()
            if accessible_stores.exists():
                queryset = queryset.filter(store__in=accessible_stores)
        
        return queryset

class DataUploadCreateView(generics.CreateAPIView):
    """Create new data upload and trigger processing"""
    serializer_class = DataUploadCreateSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create upload record
        upload = serializer.save()
        
        # Trigger async processing
        try:
            task = process_data_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save()
            
            logger.info(f"Data upload {upload.id} created and processing started", 
                       extra={'upload_id': upload.id, 'user_id': request.user.id})
            
            return Response({
                'upload_id': upload.id,
                'task_id': task.id,
                'status': 'processing_started',
                'message': 'File uploaded successfully. Processing started.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to start processing for upload {upload.id}: {str(e)}")
            upload.status = 'failed'
            upload.error_log = str(e)
            upload.save()
            
            return Response({
                'error': 'Failed to start processing',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DataUploadListView(generics.ListAPIView):
    """List data uploads for the current user"""
    serializer_class = DataUploadSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = DataUpload.objects.filter(created_by=self.request.user)
        return queryset

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upload_status(request, upload_id):
    """Get detailed status of a data upload"""
    upload = get_object_or_404(DataUpload, id=upload_id, created_by=request.user)
    
    # Check Celery task status if available
    task_status = None
    if upload.celery_task_id:
        try:
            task_result = AsyncResult(upload.celery_task_id)
            task_status = {
                'state': task_result.state,
                'info': task_result.info if hasattr(task_result, 'info') else None,
            }
        except Exception as e:
            logger.warning(f"Could not get task status: {str(e)}")
    
    # Get validation errors if any
    validation_errors = DataValidationError.objects.filter(upload=upload)[:10]  # Limit to first 10
    
    response_data = {
        'upload': DataUploadSerializer(upload).data,
        'task_status': task_status,
        'validation_errors': DataValidationErrorSerializer(validation_errors, many=True).data,
        'has_more_errors': validation_errors.count() > 10
    }
    
    return Response(response_data)

class DataQualityReportListView(generics.ListAPIView):
    """List data quality reports"""
    queryset = DataQualityReport.objects.all()
    serializer_class = DataQualityReportSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_data_quality_check(request):
    """Trigger data quality assessment"""
    from .tasks import generate_data_quality_report
    
    date_from = request.data.get('date_from')
    date_to = request.data.get('date_to')
    
    if not date_from or not date_to:
        return Response({
            'error': 'date_from and date_to parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        task = generate_data_quality_report.delay(date_from, date_to)
        
        logger.info(f"Data quality check triggered by user {request.user.id}",
                   extra={'date_from': date_from, 'date_to': date_to})
        
        return Response({
            'task_id': task.id,
            'message': 'Data quality check started',
            'status': 'processing'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Failed to start data quality check: {str(e)}")
        return Response({
            'error': 'Failed to start data quality check',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)