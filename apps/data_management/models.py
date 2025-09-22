from django.db import models
from django.contrib.auth.models import User
from apps.core.models import BaseModel, Store, Product

class SalesData(BaseModel):
    """Sales data model"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date = models.DateField()
    sales = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    on_hand = models.IntegerField()
    promotions_flag = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['store', 'product', 'date']
        ordering = ['-date', 'store', 'product']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['store', 'product']),
            models.Index(fields=['date', 'store']),
        ]
    
    def __str__(self):
        return f"{self.store.store_id} - {self.product.sku_id} - {self.date}"

class DataUpload(BaseModel):
    """Track data upload jobs"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    file = models.FileField(upload_to='uploads/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_records = models.IntegerField(null=True, blank=True)
    processed_records = models.IntegerField(default=0)
    error_records = models.IntegerField(default=0)
    error_log = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.original_filename} - {self.status}"

class DataValidationError(BaseModel):
    """Track data validation errors"""
    upload = models.ForeignKey(DataUpload, on_delete=models.CASCADE, related_name='validation_errors')
    row_number = models.IntegerField()
    column_name = models.CharField(max_length=100, blank=True)
    error_type = models.CharField(max_length=100)
    error_message = models.TextField()
    raw_value = models.TextField(blank=True)
    
    class Meta:
        ordering = ['upload', 'row_number']
    
    def __str__(self):
        return f"{self.upload.original_filename} - Row {self.row_number}: {self.error_type}"

class DataQualityReport(BaseModel):
    """Data quality assessment reports"""
    date_range_start = models.DateField()
    date_range_end = models.DateField()
    total_records = models.IntegerField()
    missing_values_count = models.JSONField(default=dict)
    outliers_count = models.JSONField(default=dict)
    duplicate_records = models.IntegerField(default=0)
    quality_score = models.FloatField()
    recommendations = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Quality Report {self.date_range_start} to {self.date_range_end}"