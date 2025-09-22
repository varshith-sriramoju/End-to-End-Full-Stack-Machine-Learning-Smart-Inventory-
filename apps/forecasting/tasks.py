"""
Celery tasks for forecasting operations
"""

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from .models import MLModel, ForecastPrediction, BatchPredictionJob, InventoryAlert
from .ml_service import MLService
from apps.core.models import Store, Product
from apps.data_management.models import SalesData
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def batch_predict(self, job_id):
    """Execute batch prediction job"""
    try:
        job = BatchPredictionJob.objects.get(id=job_id)
        job.status = 'processing'
        job.save()
        
        logger.info(f"Starting batch prediction job {job_id}")
        
        # Initialize ML service
        ml_service = MLService()
        if not ml_service.is_model_loaded():
            raise Exception("No ML model available")
        
        # Get stores and products to predict
        stores = Store.objects.filter(is_active=True)
        products = Product.objects.filter(is_active=True)
        
        if job.stores_filter:
            stores = stores.filter(store_id__in=job.stores_filter)
        if job.products_filter:
            products = products.filter(sku_id__in=job.products_filter)
        
        # Generate date range
        current_date = job.prediction_date_start
        dates = []
        while current_date <= job.prediction_date_end:
            dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Calculate total predictions needed
        total_predictions = len(stores) * len(products) * len(dates)
        job.total_predictions = total_predictions
        job.save()
        
        # Process predictions in batches
        batch_size = 100
        completed = 0
        predictions_batch = []
        
        for store in stores:
            for product in products:
                for pred_date in dates:
                    try:
                        # Make prediction
                        prediction_result = ml_service.predict_single(
                            store.store_id, 
                            product.sku_id, 
                            pred_date
                        )
                        
                        if prediction_result:
                            # Create prediction record
                            prediction = ForecastPrediction(
                                model=job.model,
                                store=store,
                                product=product,
                                prediction_date=pred_date,
                                predicted_demand=prediction_result['demand'],
                                confidence_interval_lower=prediction_result['confidence_interval']['lower'],
                                confidence_interval_upper=prediction_result['confidence_interval']['upper']
                            )
                            predictions_batch.append(prediction)
                        
                        completed += 1
                        
                        # Bulk create when batch is full
                        if len(predictions_batch) >= batch_size:
                            ForecastPrediction.objects.bulk_create(
                                predictions_batch, 
                                ignore_conflicts=True
                            )
                            predictions_batch = []
                            
                            # Update progress
                            job.completed_predictions = completed
                            job.save()
                            
                            # Update task progress
                            self.update_state(
                                state='PROGRESS',
                                meta={
                                    'completed': completed,
                                    'total': total_predictions,
                                    'percentage': (completed / total_predictions) * 100
                                }
                            )
                    
                    except Exception as e:
                        logger.error(f"Error predicting {store.store_id}-{product.sku_id}-{pred_date}: {str(e)}")
                        continue
        
        # Create remaining predictions
        if predictions_batch:
            ForecastPrediction.objects.bulk_create(
                predictions_batch, 
                ignore_conflicts=True
            )
        
        job.status = 'completed'
        job.completed_predictions = completed
        job.save()
        
        logger.info(f"Batch prediction job {job_id} completed: {completed}/{total_predictions}")
        
        # Generate alerts based on predictions
        generate_inventory_alerts.delay(job_id)
        
        return {
            'status': 'completed',
            'completed': completed,
            'total': total_predictions
        }
        
    except Exception as e:
        logger.error(f"Batch prediction job {job_id} failed: {str(e)}")
        
        try:
            job = BatchPredictionJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_log = str(e)
            job.save()
        except:
            pass
        
        return {'status': 'failed', 'error': str(e)}

@shared_task(bind=True)
def retrain_model(self, model_name=None, hyperparameters=None, data_date_from=None, data_date_to=None, user_id=None):
    """Retrain ML model"""
    try:
        logger.info(f"Starting model retraining triggered by user {user_id}")
        
        # Import here to avoid circular imports
        from ml.scripts.train import DemandForecaster
        
        # Initialize forecaster
        forecaster = DemandForecaster(model_name=model_name)
        
        # Parse dates if provided
        date_from = datetime.strptime(data_date_from, '%Y-%m-%d').date() if data_date_from else None
        date_to = datetime.strptime(data_date_to, '%Y-%m-%d').date() if data_date_to else None
        
        # Train model
        self.update_state(state='PROGRESS', meta={'step': 'training'})
        metrics = forecaster.train(
            data_date_from=date_from,
            data_date_to=date_to,
            hyperparameters=hyperparameters or {}
        )
        
        # Save model
        self.update_state(state='PROGRESS', meta={'step': 'saving'})
        model = forecaster.save_model(metrics, data_version='retrained')
        
        logger.info(f"Model retraining completed: {model.id}")
        
        return {
            'status': 'completed',
            'model_id': str(model.id),
            'metrics': metrics
        }
        
    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

@shared_task
def generate_inventory_alerts(job_id=None):
    """Generate inventory alerts based on predictions"""
    try:
        logger.info("Generating inventory alerts...")
        
        # Get recent predictions
        cutoff_date = timezone.now().date() + timedelta(days=30)
        predictions = ForecastPrediction.objects.filter(
            prediction_date__lte=cutoff_date,
            prediction_date__gte=timezone.now().date()
        ).select_related('store', 'product')
        
        alerts_created = 0
        
        for prediction in predictions:
            try:
                # Get current inventory
                latest_sales = SalesData.objects.filter(
                    store=prediction.store,
                    product=prediction.product
                ).order_by('-date').first()
                
                if not latest_sales:
                    continue
                
                current_inventory = latest_sales.on_hand
                predicted_demand = prediction.predicted_demand
                
                # Check for stockout risk
                if current_inventory < predicted_demand * 1.5:  # Safety stock threshold
                    # Calculate stockout date
                    days_until_stockout = max(1, int(current_inventory / max(predicted_demand, 1)))
                    stockout_date = timezone.now().date() + timedelta(days=days_until_stockout)
                    
                    # Determine priority
                    if days_until_stockout <= 3:
                        priority = 'critical'
                    elif days_until_stockout <= 7:
                        priority = 'high'
                    elif days_until_stockout <= 14:
                        priority = 'medium'
                    else:
                        priority = 'low'
                    
                    # Create alert if it doesn't exist
                    alert, created = InventoryAlert.objects.get_or_create(
                        store=prediction.store,
                        product=prediction.product,
                        alert_type='stockout_risk',
                        is_acknowledged=False,
                        defaults={
                            'priority': priority,
                            'message': f"Potential stockout in {days_until_stockout} days. Current inventory: {current_inventory}, Predicted demand: {predicted_demand:.1f}",
                            'predicted_stockout_date': stockout_date,
                            'current_inventory': current_inventory,
                            'recommended_action': f"Reorder {int(predicted_demand * 2)} units to maintain safety stock"
                        }
                    )
                    
                    if created:
                        alerts_created += 1
                
                # Check for overstock
                elif current_inventory > predicted_demand * 4:  # Overstock threshold
                    alert, created = InventoryAlert.objects.get_or_create(
                        store=prediction.store,
                        product=prediction.product,
                        alert_type='overstock_risk',
                        is_acknowledged=False,
                        defaults={
                            'priority': 'low',
                            'message': f"Potential overstock. Current inventory: {current_inventory}, Predicted demand: {predicted_demand:.1f}",
                            'current_inventory': current_inventory,
                            'recommended_action': "Consider promotional activities to reduce inventory"
                        }
                    )
                    
                    if created:
                        alerts_created += 1
                        
            except Exception as e:
                logger.error(f"Error generating alert for {prediction.store.store_id}-{prediction.product.sku_id}: {str(e)}")
                continue
        
        logger.info(f"Generated {alerts_created} new inventory alerts")
        return {'alerts_created': alerts_created}
        
    except Exception as e:
        logger.error(f"Error generating inventory alerts: {str(e)}")
        return {'error': str(e)}

@shared_task
def model_health_check():
    """Check model performance and trigger retraining if needed"""
    try:
        logger.info("Running model health check...")
        
        # Get active model
        active_model = MLModel.objects.filter(is_active=True).first()
        if not active_model:
            logger.warning("No active model found")
            return {'status': 'no_model'}
        
        # Check if model is too old (older than 30 days)
        days_since_training = (timezone.now().date() - active_model.training_date.date()).days
        
        if days_since_training > 30:
            logger.info(f"Model is {days_since_training} days old, triggering retraining")
            retrain_model.delay()
            return {'status': 'retraining_triggered', 'reason': 'model_age'}
        
        # Check recent prediction accuracy
        recent_predictions = ForecastPrediction.objects.filter(
            model=active_model,
            actual_demand__isnull=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        
        if recent_predictions.exists():
            # Calculate recent MAPE
            total_error = 0
            total_actual = 0
            
            for pred in recent_predictions:
                error = abs(pred.predicted_demand - pred.actual_demand)
                total_error += error
                total_actual += pred.actual_demand
            
            if total_actual > 0:
                recent_mape = (total_error / total_actual) * 100
                threshold = getattr(settings, 'MODEL_RETRAIN_THRESHOLD', 15) * 100  # Convert to percentage
                
                if recent_mape > threshold:
                    logger.info(f"Model performance degraded (MAPE: {recent_mape:.2f}%), triggering retraining")
                    retrain_model.delay()
                    return {'status': 'retraining_triggered', 'reason': 'performance_degradation', 'mape': recent_mape}
        
        logger.info("Model health check passed")
        return {'status': 'healthy'}
        
    except Exception as e:
        logger.error(f"Model health check failed: {str(e)}")
        return {'status': 'error', 'error': str(e)}