from rest_framework import serializers
from products.serializers import ProductSerializer  # Assuming you have a serializer for Product model
from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = [
            'id', 
            'product', 
            'quantity', 
            'size', 
            'sleeve', 
            'price', 
            'custom_length', 
            'length', 
            'offer_type', 
            'discount_amount', 
            'free_product'
        ]
        read_only_fields = ['id', 'price', 'discount_amount', 'free_product']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id', 
            'user', 
            'items', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
