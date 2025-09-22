from rest_framework import serializers
from .models import SalesData, DataUpload, DataValidationError, DataQualityReport
from apps.core.models import Store, Product

class SalesDataSerializer(serializers.ModelSerializer):
    store_id = serializers.CharField(source='store.store_id', read_only=True)
    sku_id = serializers.CharField(source='product.sku_id', read_only=True)
    
    class Meta:
        model = SalesData
        fields = [
            'id', 'store_id', 'sku_id', 'date', 'sales', 
            'price', 'on_hand', 'promotions_flag', 
            'created_at', 'updated_at'
        ]

class DataUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = DataUpload
        fields = [
            'id', 'file', 'original_filename', 'status', 
            'total_records', 'processed_records', 'error_records',
            'progress_percentage', 'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.total_records and obj.total_records > 0:
            return round((obj.processed_records / obj.total_records) * 100, 2)
        return 0

class DataValidationErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataValidationError
        fields = [
            'id', 'row_number', 'column_name', 'error_type',
            'error_message', 'raw_value', 'created_at'
        ]

class DataQualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataQualityReport
        fields = [
            'id', 'date_range_start', 'date_range_end', 'total_records',
            'missing_values_count', 'outliers_count', 'duplicate_records',
            'quality_score', 'recommendations', 'created_at'
        ]

class DataUploadCreateSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    
    class Meta:
        model = DataUpload
        fields = ['file']
    
    def validate_file(self, value):
        # Check file extension
        if not value.name.lower().endswith(('.csv', '.xlsx')):
            raise serializers.ValidationError(
                "Only CSV and Excel files are allowed."
            )
        
        # Check file size (50MB limit)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size cannot exceed 50MB."
            )
        
        return value
    
    def create(self, validated_data):
        validated_data['original_filename'] = validated_data['file'].name
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)