# serializers.py (pour API REST si nécessaire)
from rest_framework import serializers
from .models import *

class LunchBoxSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    rating = serializers.SerializerMethodField()
    
    class Meta:
        model = LunchBox
        fields = ['id', 'name', 'slug', 'category_name', 'description', 
                 'price', 'image', 'is_vegetarian', 'is_vegan', 
                 'is_gluten_free', 'rating', 'is_available']
    
    def get_rating(self, obj):
        return obj.get_rating()

class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['order_number', 'status', 'delivery_date', 'delivery_time',
                 'total_amount', 'items', 'created_at']
    
    def get_items(self, obj):
        return [{
            'name': item.lunch_box.name,
            'quantity': item.quantity,
            'price': item.unit_price
        } for item in obj.items.all()]