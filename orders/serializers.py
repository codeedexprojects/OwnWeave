from rest_framework import serializers
from accounts.models import CustomUser
from accounts.serializers import AddressSerializer
from products.models import Product
from .models import Order, OrderItem
from cart.models import Cart
# from products.serializers import ProductImageSerializer
from orders.models import AdminOrder



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['name', 'mobile_number', 'email']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description','product_code','color', 'offer_price_per_meter',]  # Add any other fields you need

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    product_code = serializers.CharField(source='product.product_code',read_only=True)
    product_color = serializers.CharField(source='product.color',read_only=True)

    class Meta:
        model = OrderItem
        fields = ['product','product_code','product_color' ,'quantity', 'size', 'sleeve', 'price']

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)  # User details should not be updated here
    shipping_address = AddressSerializer(read_only=True)  # Shipping address remains read-only
    items = OrderItemSerializer(many=True, read_only=True)  # Order items are not editable
    product_images = serializers.SerializerMethodField()


    class Meta:
        model = Order
        fields = [
            'id', 'user', 'shipping_address', 'total_price', 'status','Track_id','return_status','product_images',
            'payment_option', 'payment_status', 'created_at', 'items'
        ]
        read_only_fields = ['id', 'user', 'total_price', 'created_at', 'items']


    def get_product_images(self, obj):
        """
        Retrieve all product images related to the items in the order.
        """
        images = []
        for item in obj.items.all():
            product = item.product
            product_images = product.images.all()  # Assuming `ProductImage` is related to `Product` via `related_name="images"`
            for img in product_images:
                images.append(img.image.url)  # Include the image URL
        return images


class PaymentDetailsSerializer(serializers.ModelSerializer):
    user = UserSerializer()  # Serialize the user data

    class Meta:
        model = Order
        fields = ['id', 'user', 'total_price', 'payment_status', 'payment_option', 'created_at']

class AdminOrderSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_details = serializers.SerializerMethodField()


    class Meta:
        model = AdminOrder
        fields = [
            'id', 'name', 'phoneNumber', 'address', 'state', 'pincode', 'city', 'district',
            'productCode', 'product_name','product_details', 'size', 'customSize', 'quantity', 'paymentMethod',
            'paymentStatus', 'sleeveType', 'total_price','created_at'
        ]

    def get_product_details(self, obj):
        try:
            product = Product.objects.get(id=obj.productCode.id)
            return {
                "name": product.name,
                "product_code" : product.product_code,
                "category": product.category.name if product.category else None,
                "price_per_meter": product.price_per_meter,
                "offer_price_per_meter": product.offer_price_per_meter,
                "description": product.description,
                "fabric": product.fabric,
                "color": product.color,
            }
        except Product.DoesNotExist:
            return None