"""
Pytest configuration and fixtures
"""

import pytest
import os
import django
from django.conf import settings
from django.test.utils import get_runner

def pytest_configure():
    """Configure Django settings for testing"""
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'rest_framework',
            'rest_framework.authtoken',
            'apps.core',
            'apps.authentication',
            'apps.data_management',
            'apps.forecasting',
            'apps.dashboard',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        ROOT_URLCONF='smartinventory.urls',
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ],
        REST_FRAMEWORK={
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'rest_framework.authentication.TokenAuthentication',
            ],
            'DEFAULT_PERMISSION_CLASSES': [
                'rest_framework.permissions.IsAuthenticated',
            ],
        },
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
        },
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )
    django.setup()

@pytest.fixture
def api_client():
    """DRF API client"""
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def user():
    """Create test user"""
    from django.contrib.auth.models import User
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def admin_user():
    """Create admin user"""
    from django.contrib.auth.models import User
    from apps.core.models import UserProfile
    
    user = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        is_staff=True
    )
    
    UserProfile.objects.create(
        user=user,
        role='admin'
    )
    
    return user

@pytest.fixture
def store():
    """Create test store"""
    from apps.core.models import Store
    return Store.objects.create(
        store_id='TEST001',
        name='Test Store',
        location='Test City'
    )

@pytest.fixture
def product():
    """Create test product"""
    from apps.core.models import Product
    return Product.objects.create(
        sku_id='TEST001',
        name='Test Product',
        category='Test Category'
    )

@pytest.fixture
def sales_data(store, product, user):
    """Create test sales data"""
    from apps.data_management.models import SalesData
    from datetime import date
    from decimal import Decimal
    
    return SalesData.objects.create(
        store=store,
        product=product,
        date=date.today(),
        sales=Decimal('10.50'),
        price=Decimal('25.99'),
        on_hand=100,
        promotions_flag=False,
        created_by=user
    )