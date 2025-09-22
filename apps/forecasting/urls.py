from django.urls import path
from . import views

app_name = 'forecasting'

urlpatterns = [
    # Models
    path('models/', views.MLModelListView.as_view(), name='model-list'),
    path('models/retrain/', views.trigger_model_retrain, name='model-retrain'),
    path('models/performance/', views.ModelPerformanceListView.as_view(), name='model-performance'),
    
    # Predictions
    path('predict/', views.predict_demand, name='predict'),
    path('predict/batch/', views.batch_predict_demand, name='batch-predict'),
    path('predictions/', views.ForecastPredictionListView.as_view(), name='prediction-list'),
    
    # Batch jobs
    path('batch-jobs/', views.BatchPredictionJobListView.as_view(), name='batch-job-list'),
    path('batch-jobs/<uuid:job_id>/status/', views.batch_job_status, name='batch-job-status'),
    
    # Alerts
    path('alerts/', views.InventoryAlertListView.as_view(), name='alert-list'),
    path('alerts/<uuid:alert_id>/acknowledge/', views.acknowledge_alert, name='alert-acknowledge'),
]