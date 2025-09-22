from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import DataUpload, SalesData, DataValidationError, DataQualityReport
from apps.core.models import Store, Product
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_data_upload(self, upload_id):
    """Process uploaded CSV/Excel file"""
    try:
        upload = DataUpload.objects.get(id=upload_id)
        upload.status = 'processing'
        upload.save()
        
        logger.info(f"Starting processing for upload {upload_id}")
        
        # Read the file
        file_path = upload.file.path
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        upload.total_records = len(df)
        upload.save()
        
        # Validate required columns
        required_columns = ['date', 'store_id', 'sku_id', 'sales', 'price', 'on_hand', 'promotions_flag']
        missing_columns = set(required_columns) - set(df.columns)
        
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}"
            upload.status = 'failed'
            upload.error_log = error_msg
            upload.save()
            return {'status': 'failed', 'error': error_msg}
        
        # Process data in chunks
        chunk_size = 1000
        processed_count = 0
        error_count = 0
        
        for chunk_start in range(0, len(df), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(df))
            chunk_df = df.iloc[chunk_start:chunk_end]
            
            processed, errors = _process_chunk(chunk_df, upload, chunk_start)
            processed_count += processed
            error_count += errors
            
            # Update progress
            upload.processed_records = processed_count
            upload.error_records = error_count
            upload.save()
            
            # Update task progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'processed': processed_count,
                    'total': upload.total_records,
                    'errors': error_count
                }
            )
        
        upload.status = 'completed'
        upload.save()
        
        logger.info(f"Upload {upload_id} completed: {processed_count} processed, {error_count} errors")
        
        return {
            'status': 'completed',
            'processed': processed_count,
            'errors': error_count,
            'total': upload.total_records
        }
        
    except Exception as e:
        logger.error(f"Error processing upload {upload_id}: {str(e)}")
        
        try:
            upload = DataUpload.objects.get(id=upload_id)
            upload.status = 'failed'
            upload.error_log = str(e)
            upload.save()
        except:
            pass
        
        return {'status': 'failed', 'error': str(e)}

def _process_chunk(chunk_df, upload, chunk_start):
    """Process a chunk of data"""
    processed_count = 0
    error_count = 0
    
    with transaction.atomic():
        for idx, row in chunk_df.iterrows():
            try:
                # Validate and get/create store
                store, created = Store.objects.get_or_create(
                    store_id=str(row['store_id']),
                    defaults={'name': f"Store {row['store_id']}"}
                )
                
                # Validate and get/create product
                product, created = Product.objects.get_or_create(
                    sku_id=str(row['sku_id']),
                    defaults={'name': f"Product {row['sku_id']}"}
                )
                
                # Parse date
                date_value = pd.to_datetime(row['date']).date()
                
                # Validate numeric fields
                sales = float(row['sales']) if pd.notna(row['sales']) else 0.0
                price = float(row['price']) if pd.notna(row['price']) else 0.0
                on_hand = int(row['on_hand']) if pd.notna(row['on_hand']) else 0
                promotions_flag = bool(row['promotions_flag']) if pd.notna(row['promotions_flag']) else False
                
                # Create or update sales data
                SalesData.objects.update_or_create(
                    store=store,
                    product=product,
                    date=date_value,
                    defaults={
                        'sales': sales,
                        'price': price,
                        'on_hand': on_hand,
                        'promotions_flag': promotions_flag,
                        'created_by': upload.created_by
                    }
                )
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                
                # Log validation error
                DataValidationError.objects.create(
                    upload=upload,
                    row_number=chunk_start + idx + 1,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    raw_value=str(row.to_dict())
                )
    
    return processed_count, error_count

@shared_task
def generate_data_quality_report(date_from, date_to):
    """Generate data quality assessment report"""
    try:
        logger.info(f"Generating data quality report from {date_from} to {date_to}")
        
        # Convert string dates to date objects
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        # Get data for the date range
        queryset = SalesData.objects.filter(date__range=[start_date, end_date])
        
        if not queryset.exists():
            return {'status': 'completed', 'message': 'No data found for the specified date range'}
        
        # Convert to DataFrame for analysis
        data = list(queryset.values(
            'date', 'sales', 'price', 'on_hand', 'promotions_flag',
            'store__store_id', 'product__sku_id'
        ))
        df = pd.DataFrame(data)
        
        # Analyze data quality
        total_records = len(df)
        missing_values = df.isnull().sum().to_dict()
        
        # Detect outliers using IQR method
        outliers = {}
        for col in ['sales', 'price', 'on_hand']:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers[col] = len(df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)])
        
        # Check for duplicates
        duplicates = df.duplicated(subset=['date', 'store__store_id', 'product__sku_id']).sum()
        
        # Calculate quality score (0-100)
        missing_penalty = sum(missing_values.values()) / (total_records * len(missing_values)) * 30
        outlier_penalty = sum(outliers.values()) / total_records * 20
        duplicate_penalty = duplicates / total_records * 50
        
        quality_score = max(0, 100 - missing_penalty - outlier_penalty - duplicate_penalty)
        
        # Generate recommendations
        recommendations = []
        if sum(missing_values.values()) > 0:
            recommendations.append("Address missing values in the dataset")
        if sum(outliers.values()) > total_records * 0.05:
            recommendations.append("Investigate potential data entry errors causing outliers")
        if duplicates > 0:
            recommendations.append("Remove duplicate records to improve data integrity")
        
        # Create report
        report = DataQualityReport.objects.create(
            date_range_start=start_date,
            date_range_end=end_date,
            total_records=total_records,
            missing_values_count=missing_values,
            outliers_count=outliers,
            duplicate_records=duplicates,
            quality_score=round(quality_score, 2),
            recommendations='\n'.join(recommendations) if recommendations else 'Data quality looks good!'
        )
        
        logger.info(f"Data quality report {report.id} generated successfully")
        
        return {
            'status': 'completed',
            'report_id': str(report.id),
            'quality_score': quality_score,
            'total_records': total_records
        }
        
    except Exception as e:
        logger.error(f"Error generating data quality report: {str(e)}")
        return {'status': 'failed', 'error': str(e)}

@shared_task
def data_quality_check():
    """Scheduled data quality check"""
    # Check data from last 7 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    return generate_data_quality_report(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )