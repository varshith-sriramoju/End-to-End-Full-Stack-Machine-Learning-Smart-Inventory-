"""
Machine learning tests
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import date, datetime, timedelta

@pytest.mark.django_db
class TestMLService:
    """Test ML service functionality"""
    
    def test_ml_service_initialization(self):
        """Test ML service initialization"""
        from apps.forecasting.ml_service import MLService
        
        service = MLService()
        
        # Should initialize without errors
        assert service is not None
        assert hasattr(service, 'model')
        assert hasattr(service, 'label_encoders')
        assert hasattr(service, 'feature_columns')
    
    @patch('apps.forecasting.ml_service.MLModel')
    @patch('joblib.load')
    def test_load_active_model(self, mock_joblib_load, mock_ml_model):
        """Test loading active model"""
        from apps.forecasting.ml_service import MLService
        
        # Mock active model
        mock_model_instance = Mock()
        mock_model_instance.id = 1
        mock_model_instance.name = 'test_model'
        mock_model_instance.model_file_path = '/path/to/model.joblib'
        
        mock_ml_model.objects.filter.return_value.first.return_value = mock_model_instance
        
        # Mock joblib load
        mock_joblib_load.return_value = {
            'model': Mock(),
            'label_encoders': {'store_id': Mock(), 'sku_id': Mock()},
            'feature_columns': ['feature1', 'feature2']
        }
        
        service = MLService()
        
        assert service.model is not None
        assert len(service.label_encoders) == 2
        assert len(service.feature_columns) == 2
    
    def test_predict_single_no_model(self):
        """Test prediction with no model loaded"""
        from apps.forecasting.ml_service import MLService
        
        service = MLService()
        service.model = None
        
        result = service.predict_single('STORE001', 'SKU001', '2024-01-01')
        
        assert result is None
    
    @patch('apps.forecasting.ml_service.SalesData')
    def test_prepare_features_no_data(self, mock_sales_data):
        """Test feature preparation with no historical data"""
        from apps.forecasting.ml_service import MLService
        
        mock_sales_data.objects.filter.return_value.order_by.return_value.values.return_value = []
        
        service = MLService()
        service.label_encoders = {'store_id': Mock(), 'sku_id': Mock()}
        
        result = service._prepare_features_for_prediction('STORE001', 'SKU001', date.today())
        
        assert result is None

class TestDemandForecaster:
    """Test demand forecasting training"""
    
    def test_forecaster_initialization(self):
        """Test forecaster initialization"""
        from ml.scripts.train import DemandForecaster
        
        forecaster = DemandForecaster(model_name='test_model')
        
        assert forecaster.model_name == 'test_model'
        assert forecaster.model is None
        assert len(forecaster.label_encoders) == 0
        assert len(forecaster.feature_columns) == 0
    
    def test_prepare_features(self):
        """Test feature preparation"""
        from ml.scripts.train import DemandForecaster
        
        # Create sample data
        data = {
            'store_id': ['STORE001'] * 100,
            'sku_id': ['SKU001'] * 100,
            'date': pd.date_range('2024-01-01', periods=100),
            'sales': np.random.uniform(1, 20, 100),
            'price': np.random.uniform(10, 50, 100),
            'on_hand': np.random.randint(10, 200, 100),
            'promotions_flag': np.random.choice([0, 1], 100)
        }
        df = pd.DataFrame(data)
        
        forecaster = DemandForecaster()
        result_df = forecaster.prepare_features(df)
        
        assert len(result_df) > 0
        assert 'store_id_encoded' in result_df.columns
        assert 'sku_id_encoded' in result_df.columns
        assert 'sales_lag_1' in result_df.columns
        assert 'sales_rolling_7' in result_df.columns
    
    def test_feature_columns_defined(self):
        """Test that feature columns are properly defined"""
        from ml.scripts.train import DemandForecaster
        
        forecaster = DemandForecaster()
        
        # Create sample data and prepare features
        data = {
            'store_id': ['STORE001'] * 50,
            'sku_id': ['SKU001'] * 50,
            'date': pd.date_range('2024-01-01', periods=50),
            'sales': np.random.uniform(1, 20, 50),
            'price': np.random.uniform(10, 50, 50),
            'on_hand': np.random.randint(10, 200, 50),
            'promotions_flag': np.random.choice([0, 1], 50)
        }
        df = pd.DataFrame(data)
        
        result_df = forecaster.prepare_features(df)
        
        # Check that all feature columns exist
        for col in forecaster.feature_columns:
            assert col in result_df.columns, f"Feature column {col} not found"

@pytest.mark.django_db
class TestCeleryTasks:
    """Test Celery tasks"""
    
    @patch('apps.forecasting.tasks.MLService')
    def test_batch_predict_task(self, mock_ml_service, store, product):
        """Test batch prediction task"""
        from apps.forecasting.tasks import batch_predict
        from apps.forecasting.models import MLModel, BatchPredictionJob
        
        # Create test model and job
        model = MLModel.objects.create(
            name='test_model',
            version='1.0',
            algorithm='GradientBoostingRegressor',
            training_date=datetime.now()
        )
        
        job = BatchPredictionJob.objects.create(
            model=model,
            prediction_date_start=date.today(),
            prediction_date_end=date.today() + timedelta(days=1)
        )
        
        # Mock ML service
        mock_service_instance = Mock()
        mock_service_instance.is_model_loaded.return_value = True
        mock_service_instance.predict_single.return_value = {
            'demand': 15.5,
            'confidence_interval': {'lower': 12.0, 'upper': 19.0}
        }
        mock_ml_service.return_value = mock_service_instance
        
        # Run task
        result = batch_predict(job.id)
        
        assert result['status'] == 'completed'
        assert result['completed'] > 0
    
    def test_model_health_check_no_model(self):
        """Test model health check with no active model"""
        from apps.forecasting.tasks import model_health_check
        
        result = model_health_check()
        
        assert result['status'] == 'no_model'
    
    @patch('apps.forecasting.tasks.retrain_model')
    def test_model_health_check_old_model(self, mock_retrain):
        """Test model health check with old model"""
        from apps.forecasting.tasks import model_health_check
        from apps.forecasting.models import MLModel
        
        # Create old model
        old_date = datetime.now() - timedelta(days=35)
        MLModel.objects.create(
            name='old_model',
            version='1.0',
            algorithm='GradientBoostingRegressor',
            training_date=old_date,
            is_active=True
        )
        
        result = model_health_check()
        
        assert result['status'] == 'retraining_triggered'
        assert result['reason'] == 'model_age'
        mock_retrain.delay.assert_called_once()