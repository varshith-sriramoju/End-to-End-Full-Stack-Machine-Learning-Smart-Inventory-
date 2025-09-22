from django.urls import path
from . import views

app_name = 'data_management'

urlpatterns = [
    # Sales data
    path('sales/', views.SalesDataListView.as_view(), name='sales-list'),
    
    # Data uploads
    path('upload/', views.DataUploadCreateView.as_view(), name='upload-create'),
    path('uploads/', views.DataUploadListView.as_view(), name='upload-list'),
    path('uploads/<uuid:upload_id>/status/', views.upload_status, name='upload-status'),
    
    # Data quality
    path('quality/reports/', views.DataQualityReportListView.as_view(), name='quality-reports'),
    path('quality/check/', views.trigger_data_quality_check, name='quality-check'),
]