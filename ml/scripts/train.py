#!/usr/bin/env python3
"""
Production ML training script for SmartInventory demand forecasting
"""

import os
import sys
import argparse
import logging
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder
import django

# Setup Django environment (works both locally and in Docker)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartinventory.settings')
django.setup()

from apps.data_management.models import SalesData
from apps.forecasting.models import MLModel, ModelPerformanceMetric
from apps.core.models import Store, Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemandForecaster:
    """Demand forecasting model trainer"""

    def __init__(self, model_name=None):
        self.model_name = model_name or f"demand_forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.model = None
        self.label_encoders = {}
        self.feature_columns = []

    def prepare_features(self, df):
        """Prepare features for training"""
        logger.info("Preparing features...")

        # Sort by date for time series features
        df = df.sort_values(['store_id', 'sku_id', 'date'])

        # Encode categorical variables
        for col in ['store_id', 'sku_id']:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(df[col])
            else:
                df[f'{col}_encoded'] = self.label_encoders[col].transform(df[col])

        # Time-based features
        df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek
        df['month'] = pd.to_datetime(df['date']).dt.month
        df['day_of_month'] = pd.to_datetime(df['date']).dt.day
        df['quarter'] = pd.to_datetime(df['date']).dt.quarter

        # Lag features
        for lag in [1, 7, 14, 30]:
            df[f'sales_lag_{lag}'] = df.groupby(['store_id', 'sku_id'])['sales'].shift(lag)

        # Rolling averages
        for window in [7, 14, 30]:
            df[f'sales_rolling_{window}'] = df.groupby(['store_id', 'sku_id'])['sales'].rolling(window=window).mean().reset_index(0, drop=True)

        # Price features
        df['price_change'] = df.groupby(['store_id', 'sku_id'])['price'].pct_change()
        df['price_rolling_7'] = df.groupby(['store_id', 'sku_id'])['price'].rolling(window=7).mean().reset_index(0, drop=True)

        # Inventory features
        df['inventory_ratio'] = df['sales'] / (df['on_hand'] + 1)  # Add 1 to avoid division by zero

        # Promotion features
        df['promotions_flag'] = df['promotions_flag'].astype(int)

        # Define feature columns
        self.feature_columns = [
            'store_id_encoded', 'sku_id_encoded', 'day_of_week', 'month',
            'day_of_month', 'quarter', 'price', 'price_change', 'price_rolling_7',
            'on_hand', 'inventory_ratio', 'promotions_flag',
            'sales_lag_1', 'sales_lag_7', 'sales_lag_14', 'sales_lag_30',
            'sales_rolling_7', 'sales_rolling_14', 'sales_rolling_30'
        ]

        # Drop rows with NaN values (due to lag features)
        df = df.dropna(subset=self.feature_columns + ['sales'])

        logger.info(f"Prepared {len(df)} samples with {len(self.feature_columns)} features")
        return df

    def train(self, data_date_from=None, data_date_to=None, hyperparameters=None):
        """Train the demand forecasting model"""
        logger.info(f"Starting training for model: {self.model_name}")

        # Load data
        queryset = SalesData.objects.select_related('store', 'product').all()

        if data_date_from:
            queryset = queryset.filter(date__gte=data_date_from)
        if data_date_to:
            queryset = queryset.filter(date__lte=data_date_to)

        # Convert to DataFrame
        data = list(queryset.values(
            'date', 'sales', 'price', 'on_hand', 'promotions_flag',
            'store__store_id', 'product__sku_id'
        ))

        if not data:
            raise ValueError("No data available for training")

        df = pd.DataFrame(data)
        df.rename(columns={
            'store__store_id': 'store_id',
            'product__sku_id': 'sku_id'
        }, inplace=True)

        logger.info(f"Loaded {len(df)} records for training")

        # Prepare features
        df = self.prepare_features(df)

        # Prepare training data
        X = df[self.feature_columns]
        y = df['sales']

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )

        # Default hyperparameters
        default_params = {
            'n_estimators': 100,
            'learning_rate': 0.1,
            'max_depth': 6,
            'min_samples_split': 10,
            'min_samples_leaf': 4,
            'random_state': 42
        }

        if hyperparameters:
            default_params.update(hyperparameters)

        # Train model
        logger.info("Training Gradient Boosting model...")
        self.model = GradientBoostingRegressor(**default_params)
        self.model.fit(X_train, y_train)

        # Evaluate model
        train_pred = self.model.predict(X_train)
        test_pred = self.model.predict(X_test)

        # Calculate metrics
        train_mae = mean_absolute_error(y_train, train_pred)
        test_mae = mean_absolute_error(y_test, test_pred)
        train_rmse = np.sqrt(mean_squared_error(y_train, train_pred))
        test_rmse = np.sqrt(mean_squared_error(y_test, test_pred))

        # Calculate MAPE
        train_mape = np.mean(np.abs((y_train - train_pred) / (y_train + 1e-8))) * 100
        test_mape = np.mean(np.abs((y_test - test_pred) / (y_test + 1e-8))) * 100

        metrics = {
            'train_mae': float(train_mae),
            'test_mae': float(test_mae),
            'train_rmse': float(train_rmse),
            'test_rmse': float(test_rmse),
            'train_mape': float(train_mape),
            'test_mape': float(test_mape),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }

        logger.info(f"Training completed. Test MAE: {test_mae:.2f}, Test RMSE: {test_rmse:.2f}, Test MAPE: {test_mape:.2f}%")

        return metrics

    def save_model(self, metrics, data_version="latest"):
        """Save trained model to database and filesystem"""
        if not self.model:
            raise ValueError("No trained model to save")

        # Create model directory within the project
        model_dir = os.path.join(PROJECT_ROOT, "ml", "models", self.model_name)
        os.makedirs(model_dir, exist_ok=True)

        # Save model file
        model_path = os.path.join(model_dir, "model.joblib")
        joblib.dump({
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns
        }, model_path)

        # Save to database
        ml_model = MLModel.objects.create(
            name=self.model_name,
            version="1.0",
            algorithm="GradientBoostingRegressor",
            hyperparameters=self.model.get_params(),
            performance_metrics=metrics,
            model_file_path=model_path,
            is_active=True,
            training_data_version=data_version,
            training_date=datetime.now()
        )

        # Deactivate other models
        MLModel.objects.filter(is_active=True).exclude(id=ml_model.id).update(is_active=False)

        logger.info(f"Model saved: {ml_model.id}")
        return ml_model

def main():
    """Main training function"""
    parser = argparse.ArgumentParser(description='Train demand forecasting model')
    parser.add_argument('--model-name', help='Model name')
    parser.add_argument('--data-date-from', help='Start date for training data (YYYY-MM-DD)')
    parser.add_argument('--data-date-to', help='End date for training data (YYYY-MM-DD)')
    parser.add_argument('--data-version', default='latest', help='Data version identifier')

    args = parser.parse_args()

    try:
        # Initialize forecaster
        forecaster = DemandForecaster(model_name=args.model_name)

        # Parse dates
        date_from = datetime.strptime(args.data_date_from, '%Y-%m-%d').date() if args.data_date_from else None
        date_to = datetime.strptime(args.data_date_to, '%Y-%m-%d').date() if args.data_date_to else None

        # Train model
        metrics = forecaster.train(
            data_date_from=date_from,
            data_date_to=date_to
        )

        # Save model
        model = forecaster.save_model(metrics, args.data_version)

        print(f"Training completed successfully!")
        print(f"Model ID: {model.id}")
        print(f"Test MAE: {metrics['test_mae']:.2f}")
        print(f"Test RMSE: {metrics['test_rmse']:.2f}")
        print(f"Test MAPE: {metrics['test_mape']:.2f}%")

    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()