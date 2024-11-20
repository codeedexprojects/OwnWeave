from rest_framework import serializers
from .models import Offer, Product, Category, SubCategory, ProductImage, CategorySize

class OfferSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Offer
        fields = '__all__'

class CategorySizeSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = CategorySize
        fields = [
            'id', 'category', 'width', 'size_L_full_length', 'size_L_half_length',
            'size_XL_full_length', 'size_XL_half_length', 'size_XXL_full_length',
            'size_XXL_half_length', 'size_XXXL_full_length', 'size_XXXL_half_length'
        ]

class CategorySerializer(serializers.ModelSerializer):
    status = serializers.BooleanField(default=True)
    offer = OfferSerializer(read_only=True, required=False)  # Nested Offer details, now optional
    offer_id = serializers.PrimaryKeyRelatedField(
        source='offer',  # Points to the Offer ForeignKey in Category
        queryset=Offer.objects.all(),
        write_only=True,  # Used only for input, not displayed in response
        required=False,  # Make offer_id optional
        allow_null=True  # Allow null values for the offer_id field
    )
    sizes = CategorySizeSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'heading', 'description', 'offer', 'offer_id', 'image', 'status','sizes']


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = '__all__'

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_name = serializers.SerializerMethodField()
    sub_category_name = serializers.SerializerMethodField()
    offer = OfferSerializer(read_only=True)
    offer_id = serializers.PrimaryKeyRelatedField(
        source='offer', queryset=Offer.objects.all(), write_only=True,required=False
    )
    images = ProductImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    delete_image_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    available_lengths = serializers.SerializerMethodField()
    width = serializers.DecimalField(max_digits=5, decimal_places=2)  # Keep width editable

    is_visible_in_listing = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'product_code', 'category', 'category_name', 'sub_category_name',
            'width', 'price_per_meter', 'offer_price_per_meter', 'offer', 'offer_id',
            'stock_length', 'gsm', 'is_popular', 'is_offer_product', 'description',
            'fabric', 'pattern', 'fabric_composition', 'fit', 'style', 'color',
            'images', 'uploaded_images', 'delete_image_ids', 'available_lengths',
            'is_visible_in_listing', 'is_out_of_stock'
        ]

    def validate_width(self, value):
        """
        Ensure the width is valid for the selected category's CategorySize.
        """
        category = self.initial_data.get('category')
        if not category:
            raise serializers.ValidationError("Category is required to validate width.")
        
        # Fetch category sizes related to the selected category
        category_sizes = CategorySize.objects.filter(category_id=category)
        valid_widths = [cs.width for cs in category_sizes]
        
        # Check if entered width is within valid widths
        if value not in valid_widths:
            raise serializers.ValidationError(
                f"The entered width is invalid for this category. Please select a valid width: {valid_widths}"
            )
        return value

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_sub_category_name(self, obj):
        return obj.sub_category.name if obj.sub_category else None

    def get_available_lengths(self, obj):
        # Check if a CategorySize object is linked to the product's category and width
        try:
            category_size = CategorySize.objects.get(category=obj.category, width=obj.width)
            return {
                "size_L_full_length": category_size.size_L_full_length,
                "size_L_half_length": category_size.size_L_half_length,
                "size_XL_full_length": category_size.size_XL_full_length,
                "size_XL_half_length": category_size.size_XL_half_length,
                "size_XXL_full_length": category_size.size_XXL_full_length,
                "size_XXL_half_length": category_size.size_XXL_half_length,
                "size_XXXL_full_length": category_size.size_XXXL_full_length,
                "size_XXXL_half_length": category_size.size_XXXL_half_length,
            }
        except CategorySize.DoesNotExist:
            return {}  # Return an empty dictionary if no matching CategorySize found


    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        offer = validated_data.get('offer', None)

        # Set is_offer_product based on the presence of an offer
        validated_data['is_offer_product'] = bool(offer)

        # Create the product with the updated validated_data
        product = Product.objects.create(**validated_data)
        
        # Add images to the product
        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)
        
        return product

    def update(self, instance, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        delete_image_ids = validated_data.pop('delete_image_ids', [])
        offer = validated_data.get('offer', None)

        # Set is_offer_product based on the presence of an offer
        validated_data['is_offer_product'] = bool(offer)

        # Update the product with the validated data
        instance = super().update(instance, validated_data)
        
        # Delete specified images
        if delete_image_ids:
            ProductImage.objects.filter(id__in=delete_image_ids, product=instance).delete()

        # Add new images
        for image in uploaded_images:
            ProductImage.objects.create(product=instance, image=image)

        return instance

