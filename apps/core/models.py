from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='%(class)s_created'
    )
    
    class Meta:
        abstract = True

class Store(BaseModel):
    """Store model"""
    store_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['store_id']
    
    def __str__(self):
        return f"{self.store_id} - {self.name}"

class Product(BaseModel):
    """Product/SKU model"""
    sku_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['sku_id']
    
    def __str__(self):
        return f"{self.sku_id} - {self.name}"

class UserProfile(BaseModel):
    """Extended user profile"""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Store Manager'),
        ('analyst', 'Data Analyst'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='analyst')
    stores = models.ManyToManyField(Store, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"