from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from celery.result import AsyncResult
from .models import (
    MLModel, ForecastPrediction, BatchPredictionJob, 
    ModelPerformanceMetric, InventoryAlert
)
from .serializers import (
    MLModelSerializer, ForecastPredictionSerializer,
    BatchPredictionJobSerializer, ModelPerformanceMetricSerializer,
    InventoryAlertSerializer, PredictionRequestSerializer, ModelRetrainSerializer
)
from .tasks import batch_predict, retrain_model
from .ml_service import MLService
import logging

logger = logging.getLogger(__name__)

class MLModelListView(generics.ListAPIView):
    """List ML models with performance metrics"""
    queryset = MLModel.objects.all()
    serializer_class = MLModelSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-training_date']

class ForecastPredictionListView(generics.ListAPIView):
    """List forecast predictions with filtering"""
    queryset = ForecastPrediction.objects.all()
    serializer_class = ForecastPredictionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'store__store_id', 'product__sku_id', 'prediction_date',
        'model__id'
    ]
    ordering_fields = ['prediction_date', 'predicted_demand']
    ordering = ['-prediction_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user's accessible stores if not admin
        user_profile = getattr(self.request.user, 'userprofile', None)
        if user_profile and user_profile.role != 'admin':
            accessible_stores = user_profile.stores.all()
            if accessible_stores.exists():
                queryset = queryset.filter(store__in=accessible_stores)
        
        return queryset

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predict_demand(request):
    """Get real-time demand predictions"""
    store_id = request.GET.get('store_id')
    sku_id = request.GET.get('sku_id')
    date = request.GET.get('date')
    
    if not all([store_id, sku_id, date]):
        return Response({
            'error': 'store_id, sku_id, and date parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get active model
        active_model = MLModel.objects.filter(is_active=True).first()
        if not active_model:
            return Response({
                'error': 'No active model available'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Use ML service for prediction
        ml_service = MLService()
        prediction = ml_service.predict_single(store_id, sku_id, date)
        
        if prediction is None:
            return Response({
                'error': 'Unable to generate prediction'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.info(f"Generated prediction for {store_id}-{sku_id}-{date}",
                   extra={'user_id': request.user.id})
        
        return Response({
            'store_id': store_id,
            'sku_id': sku_id,
            'date': date,
            'predicted_demand': prediction['demand'],
            'confidence_interval': prediction.get('confidence_interval'),
            'model_name': active_model.name,
            'model_version': active_model.version,
            'generated_at': timezone.now()
        })
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}", extra={'user_id': request.user.id})
        return Response({
            'error': 'Prediction failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_predict_demand(request):
    """Trigger batch prediction job"""
    serializer = PredictionRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # Get active model
        active_model = MLModel.objects.filter(is_active=True).first()
        if not active_model:
            return Response({
                'error': 'No active model available'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create batch job
        batch_job = BatchPredictionJob.objects.create(
            model=active_model,
            prediction_date_start=data['date_from'],
            prediction_date_end=data['date_to'],
            stores_filter=data.get('store_ids', []),
            products_filter=data.get('sku_ids', []),
            created_by=request.user
        )
        
        # Start async processing
        task = batch_predict.delay(batch_job.id)
        batch_job.celery_task_id = task.id
        batch_job.save()
        
        logger.info(f"Batch prediction job {batch_job.id} started",
                   extra={'user_id': request.user.id})
        
        return Response({
            'job_id': batch_job.id,
            'task_id': task.id,
            'status': 'processing',
            'message': 'Batch prediction started'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Batch prediction start error: {str(e)}")
        return Response({
            'error': 'Failed to start batch prediction',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BatchPredictionJobListView(generics.ListAPIView):
    """List batch prediction jobs"""
    serializer_class = BatchPredictionJobSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return BatchPredictionJob.objects.filter(created_by=self.request.user)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_job_status(request, job_id):
    """Get batch prediction job status"""
    job = get_object_or_404(
        BatchPredictionJob, 
        id=job_id, 
        created_by=request.user
    )
    
    # Check Celery task status if available
    task_status = None
    if job.celery_task_id:
        try:
            task_result = AsyncResult(job.celery_task_id)
            task_status = {
                'state': task_result.state,
                'info': task_result.info if hasattr(task_result, 'info') else None,
            }
        except Exception as e:
            logger.warning(f"Could not get task status: {str(e)}")
    
    return Response({
        'job': BatchPredictionJobSerializer(job).data,
        'task_status': task_status
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_model_retrain(request):
    """Trigger model retraining (admin only)"""
    user_profile = getattr(request.user, 'userprofile', None)
    if not user_profile or user_profile.role != 'admin':
        return Response({
            'error': 'Only administrators can trigger model retraining'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = ModelRetrainSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        task = retrain_model.delay(
            model_name=data.get('model_name'),
            hyperparameters=data.get('hyperparameters', {}),
            data_date_from=data.get('data_date_from'),
            data_date_to=data.get('data_date_to'),
            user_id=request.user.id
        )
        
        logger.info(f"Model retraining triggered by user {request.user.id}")
        
        return Response({
            'task_id': task.id,
            'message': 'Model retraining started',
            'status': 'processing'
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Model retrain start error: {str(e)}")
        return Response({
            'error': 'Failed to start model retraining',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModelPerformanceListView(generics.ListAPIView):
    """List model performance metrics"""
    queryset = ModelPerformanceMetric.objects.all()
    serializer_class = ModelPerformanceMetricSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model__id', 'model__name']
    ordering = ['-evaluation_date']

class InventoryAlertListView(generics.ListAPIView):
    """List inventory alerts"""
    queryset = InventoryAlert.objects.all()
    serializer_class = InventoryAlertSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'store__store_id', 'product__sku_id', 'alert_type', 
        'priority', 'is_acknowledged'
    ]
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user's accessible stores if not admin
        user_profile = getattr(self.request.user, 'userprofile', None)
        if user_profile and user_profile.role != 'admin':
            accessible_stores = user_profile.stores.all()
            if accessible_stores.exists():
                queryset = queryset.filter(store__in=accessible_stores)
        
        return queryset

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_alert(request, alert_id):
    """Acknowledge an inventory alert"""
    alert = get_object_or_404(InventoryAlert, id=alert_id)
    
    # Check if user has access to this store
    user_profile = getattr(request.user, 'userprofile', None)
    if user_profile and user_profile.role != 'admin':
        accessible_stores = user_profile.stores.all()
        if accessible_stores.exists() and alert.store not in accessible_stores:
            return Response({
                'error': 'You do not have access to this store'
            }, status=status.HTTP_403_FORBIDDEN)
    
    alert.is_acknowledged = True
    alert.acknowledged_by = request.user
    alert.acknowledged_at = timezone.now()
    alert.save()
    
    logger.info(f"Alert {alert_id} acknowledged by user {request.user.id}")
    
    return Response({
        'message': 'Alert acknowledged successfully'
    })