from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from apps.data_management.models import SalesData, DataUpload
from apps.forecasting.models import ForecastPrediction, InventoryAlert, MLModel
from apps.core.models import Store, Product

def home(request):
    """Render the main dashboard page"""
    return render(request, 'dashboard/index.html')

@login_required
def dashboard_view(request):
    """Main dashboard view"""
    return render(request, 'dashboard/dashboard.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics and KPIs"""
    user = request.user
    user_profile = getattr(user, 'userprofile', None)
    
    # Get accessible stores for non-admin users
    accessible_stores = None
    if user_profile and user_profile.role != 'admin':
        accessible_stores = user_profile.stores.all()
    
    # Base querysets
    sales_qs = SalesData.objects.all()
    alerts_qs = InventoryAlert.objects.all()
    predictions_qs = ForecastPrediction.objects.all()
    
    if accessible_stores:
        sales_qs = sales_qs.filter(store__in=accessible_stores)
        alerts_qs = alerts_qs.filter(store__in=accessible_stores)
        predictions_qs = predictions_qs.filter(store__in=accessible_stores)
    
    # Date ranges
    today = timezone.now().date()
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Core statistics
    total_stores = accessible_stores.count() if accessible_stores else Store.objects.count()
    total_products = Product.objects.filter(is_active=True).count()
    total_uploads = DataUpload.objects.filter(created_by=user).count()
    
    # Recent sales data
    recent_sales = sales_qs.filter(date__gte=last_30_days).aggregate(
        total_sales=Sum('sales'),
        avg_price=Avg('price'),
        total_records=Count('id')
    )
    
    # Active alerts by priority
    alerts_by_priority = alerts_qs.filter(is_acknowledged=False).values('priority').annotate(
        count=Count('id')
    )
    alerts_summary = {alert['priority']: alert['count'] for alert in alerts_by_priority}
    
    # Stockout predictions (next 30 days)
    future_predictions = predictions_qs.filter(
        prediction_date__range=[today, today + timedelta(days=30)]
    )
    
    stockout_predictions = future_predictions.filter(
        predicted_demand__gt=0  # Simple stockout logic - can be enhanced
    ).values('store__store_id', 'product__sku_id').distinct().count()
    
    # Model performance
    active_model = MLModel.objects.filter(is_active=True).first()
    model_info = None
    if active_model:
        model_info = {
            'name': active_model.name,
            'version': active_model.version,
            'training_date': active_model.training_date,
            'performance_metrics': active_model.performance_metrics
        }
    
    # Recent upload activity
    recent_uploads = DataUpload.objects.filter(
        created_by=user,
        created_at__gte=last_7_days
    ).values('status').annotate(count=Count('id'))
    
    upload_stats = {upload['status']: upload['count'] for upload in recent_uploads}
    
    return Response({
        'overview': {
            'total_stores': total_stores,
            'total_products': total_products,
            'total_uploads': total_uploads,
            'active_alerts': sum(alerts_summary.values()),
        },
        'sales_summary': {
            'total_sales_30d': float(recent_sales['total_sales'] or 0),
            'avg_price': float(recent_sales['avg_price'] or 0),
            'records_count': recent_sales['total_records'],
        },
        'alerts_summary': alerts_summary,
        'predictions': {
            'potential_stockouts_30d': stockout_predictions,
            'total_predictions': future_predictions.count(),
        },
        'model_info': model_info,
        'upload_stats': upload_stats,
        'date_ranges': {
            'today': today,
            'last_30_days': last_30_days,
            'last_7_days': last_7_days,
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_trends(request):
    """Get sales trends data for charts"""
    user = request.user
    user_profile = getattr(user, 'userprofile', None)
    
    # Get date range from query params
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Base queryset
    sales_qs = SalesData.objects.filter(date__range=[start_date, end_date])
    
    # Filter by accessible stores if not admin
    if user_profile and user_profile.role != 'admin':
        accessible_stores = user_profile.stores.all()
        if accessible_stores.exists():
            sales_qs = sales_qs.filter(store__in=accessible_stores)
    
    # Daily sales trend
    daily_sales = sales_qs.values('date').annotate(
        total_sales=Sum('sales'),
        avg_price=Avg('price'),
        transactions=Count('id')
    ).order_by('date')
    
    # Top performing products
    top_products = sales_qs.values(
        'product__sku_id', 'product__name'
    ).annotate(
        total_sales=Sum('sales'),
        total_revenue=Sum('sales') * Avg('price')
    ).order_by('-total_sales')[:10]
    
    # Store performance
    store_performance = sales_qs.values(
        'store__store_id', 'store__name'
    ).annotate(
        total_sales=Sum('sales'),
        avg_inventory=Avg('on_hand')
    ).order_by('-total_sales')[:10]
    
    return Response({
        'daily_trends': list(daily_sales),
        'top_products': list(top_products),
        'store_performance': list(store_performance),
        'date_range': {
            'start_date': start_date,
            'end_date': end_date,
            'days': days
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forecast_accuracy(request):
    """Get forecast accuracy metrics"""
    user = request.user
    user_profile = getattr(user, 'userprofile', None)
    
    # Get predictions with actual values
    predictions_qs = ForecastPrediction.objects.exclude(actual_demand__isnull=True)
    
    # Filter by accessible stores if not admin
    if user_profile and user_profile.role != 'admin':
        accessible_stores = user_profile.stores.all()
        if accessible_stores.exists():
            predictions_qs = predictions_qs.filter(store__in=accessible_stores)
    
    # Calculate accuracy metrics by date
    accuracy_by_date = predictions_qs.values('prediction_date').annotate(
        count=Count('id'),
        avg_predicted=Avg('predicted_demand'),
        avg_actual=Avg('actual_demand')
    ).order_by('prediction_date')
    
    # Calculate overall accuracy
    total_predictions = predictions_qs.count()
    if total_predictions > 0:
        # Simple accuracy calculation (can be enhanced with more sophisticated metrics)
        accuracy_data = list(predictions_qs.values('predicted_demand', 'actual_demand'))
        
        total_error = sum(abs(p['predicted_demand'] - p['actual_demand']) for p in accuracy_data)
        mean_absolute_error = total_error / total_predictions
        
        total_actual = sum(p['actual_demand'] for p in accuracy_data)
        mean_absolute_percentage_error = (total_error / total_actual) * 100 if total_actual > 0 else 0
    else:
        mean_absolute_error = 0
        mean_absolute_percentage_error = 0
    
    return Response({
        'accuracy_by_date': list(accuracy_by_date),
        'overall_metrics': {
            'total_predictions': total_predictions,
            'mean_absolute_error': round(mean_absolute_error, 2),
            'mean_absolute_percentage_error': round(mean_absolute_percentage_error, 2),
        }
    })