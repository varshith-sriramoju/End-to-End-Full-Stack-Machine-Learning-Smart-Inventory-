from rest_framework import serializers
from .models import MLModel, ForecastPrediction, BatchPredictionJob, ModelPerformanceMetric, InventoryAlert

class MLModelSerializer(serializers.ModelSerializer):
    performance_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = MLModel
        fields = [
            'id', 'name', 'version', 'algorithm', 'hyperparameters',
            'performance_metrics', 'is_active', 'training_data_version',
            'training_date', 'performance_summary', 'created_at'
        ]
    
    def get_performance_summary(self, obj):
        """Get latest performance metrics"""
        latest_metric = ModelPerformanceMetric.objects.filter(model=obj).first()
        if latest_metric:
            return {
                'mae': latest_metric.mae,
                'rmse': latest_metric.rmse,
                'mape': latest_metric.mape,
                'evaluation_date': latest_metric.evaluation_date,
                'sample_size': latest_metric.sample_size
            }
        return None

class ForecastPredictionSerializer(serializers.ModelSerializer):
    store_id = serializers.CharField(source='store.store_id', read_only=True)
    sku_id = serializers.CharField(source='product.sku_id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = ForecastPrediction
        fields = [
            'id', 'store_id', 'sku_id', 'product_name', 'model_name',
            'prediction_date', 'predicted_demand', 
            'confidence_interval_lower', 'confidence_interval_upper',
            'actual_demand', 'created_at'
        ]

class BatchPredictionJobSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = BatchPredictionJob
        fields = [
            'id', 'model_name', 'status', 'prediction_date_start',
            'prediction_date_end', 'stores_filter', 'products_filter',
            'total_predictions', 'completed_predictions', 'progress_percentage',
            'created_at', 'updated_at'
        ]
    
    def get_progress_percentage(self, obj):
        if obj.total_predictions > 0:
            return round((obj.completed_predictions / obj.total_predictions) * 100, 2)
        return 0

class ModelPerformanceMetricSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = ModelPerformanceMetric
        fields = [
            'id', 'model_name', 'evaluation_date', 'date_range_start',
            'date_range_end', 'mae', 'rmse', 'mape', 'r2_score', 'sample_size'
        ]

class InventoryAlertSerializer(serializers.ModelSerializer):
    store_id = serializers.CharField(source='store.store_id', read_only=True)
    sku_id = serializers.CharField(source='product.sku_id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    acknowledged_by_username = serializers.CharField(
        source='acknowledged_by.username', 
        read_only=True
    )
    
    class Meta:
        model = InventoryAlert
        fields = [
            'id', 'store_id', 'sku_id', 'product_name', 'alert_type',
            'priority', 'message', 'predicted_stockout_date',
            'current_inventory', 'recommended_action', 'is_acknowledged',
            'acknowledged_by_username', 'acknowledged_at', 'created_at'
        ]

class PredictionRequestSerializer(serializers.Serializer):
    """Serializer for prediction requests"""
    store_ids = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text="List of store IDs. If not provided, predicts for all stores."
    )
    sku_ids = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        help_text="List of SKU IDs. If not provided, predicts for all products."
    )
    date_from = serializers.DateField(
        help_text="Start date for predictions (YYYY-MM-DD)"
    )
    date_to = serializers.DateField(
        help_text="End date for predictions (YYYY-MM-DD)"
    )
    
    def validate(self, data):
        if data['date_from'] > data['date_to']:
            raise serializers.ValidationError(
                "date_from must be earlier than or equal to date_to"
            )
        return data

class ModelRetrainSerializer(serializers.Serializer):
    """Serializer for model retraining requests"""
    model_name = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Name for the new model version. If not provided, auto-generated."
    )
    hyperparameters = serializers.JSONField(
        required=False,
        help_text="Custom hyperparameters for training"
    )
    data_date_from = serializers.DateField(
        required=False,
        help_text="Start date for training data. If not provided, uses all available data."
    )
    data_date_to = serializers.DateField(
        required=False,
        help_text="End date for training data"
    )
    
    def validate(self, data):
        date_from = data.get('data_date_from')
        date_to = data.get('data_date_to')
        
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                "data_date_from must be earlier than or equal to data_date_to"
            )
        
        return data