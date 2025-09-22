from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_tag
import time

def health_check(request):
    """Basic health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'smartinventory'
    })

def health_check_detailed(request):
    """Detailed health check with dependency status"""
    from django.core.cache import cache
    from django.db import connection

    status = {'status': 'healthy', 'checks': {}}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        status['checks']['database'] = 'healthy'
    except Exception as e:
        status['checks']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'

    # Redis check
    try:
        cache.set('health_check', 'ok', 30)
        cache.get('health_check')
        status['checks']['redis'] = 'healthy'
    except Exception as e:
        status['checks']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'unhealthy'

    return JsonResponse(status)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    # Favicon fallback
    path('favicon.ico', RedirectView.as_view(url=static_tag('images/favicon.svg'), permanent=False)),

    # Health checks
    path('health/', health_check, name='health'),
    path('health/detailed/', health_check_detailed, name='health-detailed'),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/auth/', include('apps.authentication.urls')),
    path('api/data/', include('apps.data_management.urls')),
    path('api/forecasting/', include('apps.forecasting.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),

    # Frontend
    path('', include('apps.dashboard.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)