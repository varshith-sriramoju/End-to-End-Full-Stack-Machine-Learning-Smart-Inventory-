"""
Model tests
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from datetime import date, datetime

@pytest.mark.django_db
class TestCoreModels:
    """Test core models"""
    
    def test_store_creation(self):
        """Test store model creation"""
        from apps.core.models import Store
        
        store = Store.objects.create(
            store_id='TEST001',
            name='Test Store',
            location='Test City'
        )
        
        assert store.store_id == 'TEST001'
        assert store.name == 'Test Store'
        assert store.is_active is True
        assert str(store) == 'TEST001 - Test Store'
    
    def test_store_unique_constraint(self):
        """Test store unique constraint"""
        from apps.core.models import Store
        
        Store.objects.create(store_id='TEST001', name='Store 1')
        
        with pytest.raises(IntegrityError):
            Store.objects.create(store_id='TEST001', name='Store 2')
    
    def test_product_creation(self):
        """Test product model creation"""
        from apps.core.models import Product
        
        product = Product.objects.create(
            sku_id='SKU001',
            name='Test Product',
            category='Electronics',
            brand='TestBrand'
        )
        
        assert product.sku_id == 'SKU001'
        assert product.name == 'Test Product'
        assert product.is_active is True
        assert str(product) == 'SKU001 - Test Product'
    
    def test_user_profile_creation(self, user):
        """Test user profile creation"""
        from apps.core.models import UserProfile, Store
        
        store = Store.objects.create(store_id='TEST001', name='Test Store')
        
        profile = UserProfile.objects.create(
            user=user,
            role='manager',
            phone='123-456-7890'
        )
        profile.stores.add(store)
        
        assert profile.user == user
        assert profile.role == 'manager'
        assert profile.stores.count() == 1
        assert str(profile) == 'testuser - manager'

@pytest.mark.django_db
class TestDataManagementModels:
    """Test data management models"""
    
    def test_sales_data_creation(self, store, product, user):
        """Test sales data creation"""
        from apps.data_management.models import SalesData
        
        sales_data = SalesData.objects.create(
            store=store,
            product=product,
            date=date.today(),
            sales=Decimal('15.50'),
            price=Decimal('29.99'),
            on_hand=50,
            promotions_flag=True,
            created_by=user
        )
        
        assert sales_data.store == store
        assert sales_data.product == product
        assert sales_data.sales == Decimal('15.50')
        assert sales_data.promotions_flag is True
    
    def test_sales_data_unique_constraint(self, store, product, user):
        """Test sales data unique constraint"""
        from apps.data_management.models import SalesData
        
        SalesData.objects.create(
            store=store,
            product=product,
            date=date.today(),
            sales=Decimal('10.00'),
            price=Decimal('20.00'),
            on_hand=100,
            created_by=user
        )
        
        with pytest.raises(IntegrityError):
            SalesData.objects.create(
                store=store,
                product=product,
                date=date.today(),
                sales=Decimal('15.00'),
                price=Decimal('25.00'),
                on_hand=80,
                created_by=user
            )
    
    def test_data_upload_creation(self, user):
        """Test data upload creation"""
        from apps.data_management.models import DataUpload
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile(
            "test.csv",
            b"date,store_id,sku_id,sales,price,on_hand,promotions_flag\n",
            content_type="text/csv"
        )
        
        upload = DataUpload.objects.create(
            file=test_file,
            original_filename='test.csv',
            created_by=user
        )
        
        assert upload.original_filename == 'test.csv'
        assert upload.status == 'pending'
        assert upload.created_by == user

@pytest.mark.django_db
class TestForecastingModels:
    """Test forecasting models"""
    
    def test_ml_model_creation(self):
        """Test ML model creation"""
        from apps.forecasting.models import MLModel
        
        model = MLModel.objects.create(
            name='test_model',
            version='1.0',
            algorithm='GradientBoostingRegressor',
            hyperparameters={'n_estimators': 100},
            performance_metrics={'mae': 2.5, 'rmse': 3.2},
            model_file_path='/path/to/model.joblib',
            training_date=datetime.now()
        )
        
        assert model.name == 'test_model'
        assert model.algorithm == 'GradientBoostingRegressor'
        assert model.is_active is False
        assert str(model) == 'test_model v1.0'
    
    def test_forecast_prediction_creation(self, store, product):
        """Test forecast prediction creation"""
        from apps.forecasting.models import MLModel, ForecastPrediction
        
        model = MLModel.objects.create(
            name='test_model',
            version='1.0',
            algorithm='GradientBoostingRegressor',
            training_date=datetime.now()
        )
        
        prediction = ForecastPrediction.objects.create(
            model=model,
            store=store,
            product=product,
            prediction_date=date.today(),
            predicted_demand=15.5,
            confidence_interval_lower=12.0,
            confidence_interval_upper=19.0
        )
        
        assert prediction.model == model
        assert prediction.predicted_demand == 15.5
        assert prediction.actual_demand is None
    
    def test_inventory_alert_creation(self, store, product):
        """Test inventory alert creation"""
        from apps.forecasting.models import InventoryAlert
        
        alert = InventoryAlert.objects.create(
            store=store,
            product=product,
            alert_type='stockout_risk',
            priority='high',
            message='Potential stockout in 3 days',
            current_inventory=5,
            recommended_action='Reorder 100 units'
        )
        
        assert alert.alert_type == 'stockout_risk'
        assert alert.priority == 'high'
        assert alert.is_acknowledged is False
        assert str(alert) == 'stockout_risk - TEST001 - TEST001'