from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Frontend views
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # API endpoints for dashboard data
    path('api/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('api/sales-trends/', views.sales_trends, name='sales-trends'),
    path('api/forecast-accuracy/', views.forecast_accuracy, name='forecast-accuracy'),
]