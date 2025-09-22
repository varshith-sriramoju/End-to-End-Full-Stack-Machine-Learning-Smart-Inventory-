from django.contrib import admin
from .models import Store, Product, UserProfile

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['store_id', 'name', 'location', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['store_id', 'name', 'location']
    ordering = ['store_id']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku_id', 'name', 'category', 'brand', 'is_active', 'created_at']
    list_filter = ['is_active', 'category', 'brand', 'created_at']
    search_fields = ['sku_id', 'name', 'category', 'brand']
    ordering = ['sku_id']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    filter_horizontal = ['stores']