from django.db import models
from apps.core.models import BaseModel, Store, Product
from django.contrib.auth.models import User
import json

class MLModel(BaseModel):
    """Machine learning model metadata"""
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    algorithm = models.CharField(max_length=100)
    hyperparameters = models.JSONField(default=dict)
    performance_metrics = models.JSONField(default=dict)
    model_file_path = models.CharField(max_length=500)
    is_active = models.BooleanField(default=False)
    training_data_version = models.CharField(max_length=100, blank=True)
    training_date = models.DateTimeField()
    
    class Meta:
        unique_together = ['name', 'version']
        ordering = ['-training_date']
    
    def __str__(self):
        return f"{self.name} v{self.version}"

class ForecastPrediction(BaseModel):
    """Store individual predictions"""
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    prediction_date = models.DateField()
    predicted_demand = models.FloatField()
    confidence_interval_lower = models.FloatField(null=True, blank=True)
    confidence_interval_upper = models.FloatField(null=True, blank=True)
    actual_demand = models.FloatField(null=True, blank=True)  # Filled later for evaluation
    
    class Meta:
        unique_together = ['model', 'store', 'product', 'prediction_date']
        ordering = ['prediction_date']
        indexes = [
            models.Index(fields=['prediction_date']),
            models.Index(fields=['store', 'product']),
            models.Index(fields=['prediction_date', 'store']),
        ]
    
    def __str__(self):
        return f"{self.store.store_id} - {self.product.sku_id} - {self.prediction_date}"

class BatchPredictionJob(BaseModel):
    """Track batch prediction jobs"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    prediction_date_start = models.DateField()
    prediction_date_end = models.DateField()
    stores_filter = models.JSONField(default=list, blank=True)  # List of store IDs
    products_filter = models.JSONField(default=list, blank=True)  # List of SKU IDs
    total_predictions = models.IntegerField(default=0)
    completed_predictions = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch Job {self.id} - {self.status}"

class ModelPerformanceMetric(BaseModel):
    """Track model performance over time"""
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE)
    evaluation_date = models.DateField()
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    mae = models.FloatField()  # Mean Absolute Error
    rmse = models.FloatField()  # Root Mean Square Error
    mape = models.FloatField()  # Mean Absolute Percentage Error
    r2_score = models.FloatField(null=True, blank=True)
    sample_size = models.IntegerField()
    
    class Meta:
        ordering = ['-evaluation_date']
        indexes = [
            models.Index(fields=['model', 'evaluation_date']),
        ]
    
    def __str__(self):
        return f"{self.model.name} - {self.evaluation_date} - MAE: {self.mae:.2f}"

class InventoryAlert(BaseModel):
    """Inventory alerts based on predictions"""
    ALERT_TYPES = [
        ('stockout_risk', 'Stockout Risk'),
        ('overstock_risk', 'Overstock Risk'),
        ('demand_spike', 'Demand Spike'),
        ('trend_change', 'Trend Change'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    message = models.TextField()
    predicted_stockout_date = models.DateField(null=True, blank=True)
    current_inventory = models.IntegerField(null=True, blank=True)
    recommended_action = models.TextField(blank=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at', 'priority']
        indexes = [
            models.Index(fields=['store', 'product']),
            models.Index(fields=['alert_type', 'priority']),
            models.Index(fields=['is_acknowledged']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.store.store_id} - {self.product.sku_id}"