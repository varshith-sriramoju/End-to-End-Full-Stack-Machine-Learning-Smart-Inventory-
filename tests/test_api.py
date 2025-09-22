"""
API endpoint tests
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from decimal import Decimal
from datetime import date

@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication endpoints"""
    
    def test_login_success(self, api_client, user):
        """Test successful login"""
        url = reverse('authentication:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'token' in response.data
        assert 'user' in response.data
        assert response.data['user']['username'] == 'testuser'
    
    def test_login_invalid_credentials(self, api_client, user):
        """Test login with invalid credentials"""
        url = reverse('authentication:login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_logout(self, api_client, user):
        """Test logout"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('authentication:logout')
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert not Token.objects.filter(user=user).exists()

@pytest.mark.django_db
class TestDataManagementAPI:
    """Test data management endpoints"""
    
    def test_sales_data_list(self, api_client, user, sales_data):
        """Test sales data list endpoint"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('data_management:sales-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['store_id'] == 'TEST001'
    
    def test_data_upload_create(self, api_client, user):
        """Test data upload creation"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # Create a simple CSV file content
        csv_content = "date,store_id,sku_id,sales,price,on_hand,promotions_flag\n2024-01-01,STORE001,SKU001,10,25.99,100,0"
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile(
            "test_data.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        url = reverse('data_management:upload-create')
        data = {'file': csv_file}
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'upload_id' in response.data
        assert 'task_id' in response.data

@pytest.mark.django_db
class TestForecastingAPI:
    """Test forecasting endpoints"""
    
    def test_models_list(self, api_client, user):
        """Test ML models list endpoint"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('forecasting:model-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_predict_demand_missing_params(self, api_client, user):
        """Test prediction endpoint with missing parameters"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('forecasting:predict')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data
    
    def test_alerts_list(self, api_client, user):
        """Test alerts list endpoint"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('forecasting:alert-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

@pytest.mark.django_db
class TestDashboardAPI:
    """Test dashboard endpoints"""
    
    def test_dashboard_stats(self, api_client, user, sales_data):
        """Test dashboard stats endpoint"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('dashboard:dashboard-stats')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'overview' in response.data
        assert 'sales_summary' in response.data
        assert 'alerts_summary' in response.data
    
    def test_sales_trends(self, api_client, user, sales_data):
        """Test sales trends endpoint"""
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('dashboard:sales-trends')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'daily_trends' in response.data
        assert 'top_products' in response.data
        assert 'store_performance' in response.data