"""
ML Service for demand forecasting predictions
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, date
from django.core.cache import cache
from django.conf import settings
from .models import MLModel, ForecastPrediction
from apps.data_management.models import SalesData
from apps.core.models import Store, Product
import logging

logger = logging.getLogger(__name__)

class MLService:
    """Service for ML model operations"""
    
    def __init__(self):
        self.model = None
        self.label_encoders = {}
        self.feature_columns = []
        self.model_metadata = None
        self._load_active_model()
    
    def _load_active_model(self):
        """Load the active ML model"""
        try:
            active_model = MLModel.objects.filter(is_active=True).first()
            if not active_model:
                logger.warning("No active ML model found")
                return
            
            # Check cache first
            cache_key = f"ml_model_{active_model.id}"
            cached_model = cache.get(cache_key)
            
            if cached_model:
                self.model = cached_model['model']
                self.label_encoders = cached_model['label_encoders']
                self.feature_columns = cached_model['feature_columns']
                self.model_metadata = active_model
                logger.info(f"Loaded cached model: {active_model.name}")
                return
            
            # Load from file
            if os.path.exists(active_model.model_file_path):
                model_data = joblib.load(active_model.model_file_path)
                self.model = model_data['model']
                self.label_encoders = model_data['label_encoders']
                self.feature_columns = model_data['feature_columns']
                self.model_metadata = active_model
                
                # Cache the model
                cache.set(cache_key, model_data, timeout=settings.PREDICTION_CACHE_TTL)
                logger.info(f"Loaded model from file: {active_model.name}")
            else:
                logger.error(f"Model file not found: {active_model.model_file_path}")
                
        except Exception as e:
            logger.error(f"Error loading ML model: {str(e)}")
    
    def _prepare_features_for_prediction(self, store_id, sku_id, target_date):
        """Prepare features for a single prediction"""
        try:
            # Get historical data for feature engineering
            end_date = target_date
            start_date = end_date - pd.Timedelta(days=60)  # Get 60 days of history
            
            # Query historical data
            historical_data = SalesData.objects.filter(
                store__store_id=store_id,
                product__sku_id=sku_id,
                date__range=[start_date, end_date]
            ).order_by('date').values(
                'date', 'sales', 'price', 'on_hand', 'promotions_flag'
            )
            
            if not historical_data:
                logger.warning(f"No historical data found for {store_id}-{sku_id}")
                return None
            
            df = pd.DataFrame(historical_data)
            df['store_id'] = store_id
            df['sku_id'] = sku_id
            
            # Encode categorical variables
            try:
                df['store_id_encoded'] = self.label_encoders['store_id'].transform([store_id])[0]
                df['sku_id_encoded'] = self.label_encoders['sku_id'].transform([sku_id])[0]
            except (KeyError, ValueError) as e:
                logger.warning(f"Unknown store_id or sku_id: {e}")
                # Use a default encoding for unknown values
                df['store_id_encoded'] = 0
                df['sku_id_encoded'] = 0
            
            # Time-based features for target date
            target_dt = pd.to_datetime(target_date)
            df['day_of_week'] = target_dt.dayofweek
            df['month'] = target_dt.month
            df['day_of_month'] = target_dt.day
            df['quarter'] = target_dt.quarter
            
            # Calculate lag features from most recent data
            recent_sales = df['sales'].values
            df['sales_lag_1'] = recent_sales[-1] if len(recent_sales) >= 1 else 0
            df['sales_lag_7'] = recent_sales[-7] if len(recent_sales) >= 7 else recent_sales[-1] if len(recent_sales) >= 1 else 0
            df['sales_lag_14'] = recent_sales[-14] if len(recent_sales) >= 14 else recent_sales[-1] if len(recent_sales) >= 1 else 0
            df['sales_lag_30'] = recent_sales[-30] if len(recent_sales) >= 30 else recent_sales[-1] if len(recent_sales) >= 1 else 0
            
            # Rolling averages
            df['sales_rolling_7'] = df['sales'].rolling(window=min(7, len(df))).mean().iloc[-1]
            df['sales_rolling_14'] = df['sales'].rolling(window=min(14, len(df))).mean().iloc[-1]
            df['sales_rolling_30'] = df['sales'].rolling(window=min(30, len(df))).mean().iloc[-1]
            
            # Price features (use most recent values)
            recent_prices = df['price'].values
            current_price = recent_prices[-1] if len(recent_prices) > 0 else 10.0
            prev_price = recent_prices[-2] if len(recent_prices) > 1 else current_price
            
            df['price'] = current_price
            df['price_change'] = (current_price - prev_price) / prev_price if prev_price > 0 else 0
            df['price_rolling_7'] = df['price'].rolling(window=min(7, len(df))).mean().iloc[-1]
            
            # Inventory features (use most recent values)
            recent_inventory = df['on_hand'].values
            current_inventory = recent_inventory[-1] if len(recent_inventory) > 0 else 50
            df['on_hand'] = current_inventory
            df['inventory_ratio'] = df['sales_lag_1'] / (current_inventory + 1)
            
            # Promotion flag (assume no promotion for prediction)
            df['promotions_flag'] = 0
            
            # Select features for prediction
            feature_row = df[self.feature_columns].iloc[-1:].fillna(0)
            
            return feature_row
            
        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            return None
    
    def predict_single(self, store_id, sku_id, target_date):
        """Make a single demand prediction"""
        if not self.model:
            logger.error("No model loaded")
            return None
        
        try:
            # Convert string date to datetime if needed
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            # Check cache first
            cache_key = f"prediction_{store_id}_{sku_id}_{target_date}"
            cached_prediction = cache.get(cache_key)
            if cached_prediction:
                return cached_prediction
            
            # Prepare features
            features = self._prepare_features_for_prediction(store_id, sku_id, target_date)
            if features is None:
                return None
            
            # Make prediction
            prediction = self.model.predict(features)[0]
            prediction = max(0, prediction)  # Ensure non-negative
            
            # Calculate confidence interval (simple approach)
            # In production, you might want to use prediction intervals from the model
            std_error = prediction * 0.2  # Assume 20% standard error
            confidence_interval = {
                'lower': max(0, prediction - 1.96 * std_error),
                'upper': prediction + 1.96 * std_error
            }
            
            result = {
                'demand': float(prediction),
                'confidence_interval': confidence_interval
            }
            
            # Cache the result
            cache.set(cache_key, result, timeout=settings.PREDICTION_CACHE_TTL)
            
            logger.info(f"Prediction for {store_id}-{sku_id}-{target_date}: {prediction:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return None
    
    def predict_batch(self, store_ids, sku_ids, date_range):
        """Make batch predictions"""
        predictions = []
        
        for store_id in store_ids:
            for sku_id in sku_ids:
                for single_date in pd.date_range(date_range[0], date_range[1]):
                    prediction = self.predict_single(store_id, sku_id, single_date.date())
                    if prediction:
                        predictions.append({
                            'store_id': store_id,
                            'sku_id': sku_id,
                            'date': single_date.date(),
                            'predicted_demand': prediction['demand'],
                            'confidence_lower': prediction['confidence_interval']['lower'],
                            'confidence_upper': prediction['confidence_interval']['upper']
                        })
        
        return predictions
    
    def is_model_loaded(self):
        """Check if a model is loaded and ready"""
        return self.model is not None
    
    def get_model_info(self):
        """Get information about the loaded model"""
        if not self.model_metadata:
            return None
        
        return {
            'id': self.model_metadata.id,
            'name': self.model_metadata.name,
            'version': self.model_metadata.version,
            'algorithm': self.model_metadata.algorithm,
            'training_date': self.model_metadata.training_date,
            'performance_metrics': self.model_metadata.performance_metrics
        }