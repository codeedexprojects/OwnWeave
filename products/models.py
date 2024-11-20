from django.db import models
from datetime import timedelta
from django.utils.timezone import now

class Offer(models.Model):
    OFFER_TYPE_CHOICES = [
        ('BOGO', 'Buy 1 Get 1 Free'),
        ('PERCENTAGE', 'Percentage Discount'),
    ]

    name = models.CharField(max_length=255)  # Offer name
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)  # For percentage offers
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.get_offer_type_display()}"


class Category(models.Model):
    name = models.CharField(max_length=255)
    heading = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    offer = models.ForeignKey('Offer', null=True, blank=True, on_delete=models.SET_NULL, related_name="categories")
    image = models.ImageField(upload_to='categories/images/', default=None)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CategorySize(models.Model):
    SIZE_CHOICES = [
        ('L', 'Large'),
        ('XL', 'Extra Large'),
        ('XXL', 'Double Extra Large'),
        ('XXXL', 'Triple Extra Large'),
    ]

    SLEEVE_CHOICES = [
        ('full', 'Full Sleeve'),
        ('half', 'Half Sleeve'),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="sizes")
    width = models.DecimalField(max_digits=5, decimal_places=2, help_text="Width in inches (e.g., 44, 60, 120)")

    # Define fields for each size and sleeve length within this width
    size_L_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_L_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXXL_full_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    size_XXXL_half_length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.category.name} - {self.width} inch width"

    def get_length(self, size, sleeve):
        # Construct the field name based on the size and sleeve
        field_name = f"size_{size}_{sleeve}_length"
        # Fetch and return the value of the corresponding field
        return getattr(self, field_name, None)



class SubCategory(models.Model):
    # Fields remain the same
    name = models.CharField(max_length=255)
    main_category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    # size = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # length = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # image = models.ImageField(upload_to='subcategories/images/')
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255, null=False)
    product_code = models.CharField(max_length=100, unique=True, default=None, null=False)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE, null=False, default=None)
    sub_category = models.ForeignKey(SubCategory, null=True, blank=True, related_name='products', on_delete=models.CASCADE)
    width = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Width in inches")
    price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, null=False)
    offer_price_per_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    offer = models.ForeignKey(Offer, null=True, blank=True, on_delete=models.SET_NULL, related_name="products")
    stock_length = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False)
    gsm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_popular = models.BooleanField(default=False)
    is_offer_product = models.BooleanField(default=False)
    description = models.TextField()
    fabric = models.CharField(max_length=255, null=True, blank=True)
    pattern = models.CharField(max_length=255, null=True, blank=True)
    fabric_composition = models.CharField(max_length=255, null=True, blank=True)
    fit = models.CharField(max_length=255, null=True, blank=True)
    style = models.CharField(max_length=255, null=True, blank=True)
    color = models.CharField(max_length=255, null=True, blank=True)
    is_out_of_stock = models.BooleanField(default=False)
    out_of_stock_date = models.DateTimeField(null=True, blank=True)
    is_visible_in_listing = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.category_size.width} inch width"

    def update_stock_status(self):
        """Update the stock status and visibility based on stock length."""
        if self.stock_length < 1.5 and not self.is_out_of_stock:
            # Mark as out of stock and set the date
            self.is_out_of_stock = True
            self.out_of_stock_date = now()
            self.is_visible_in_listing = True  # Initially visible for 10 days
        elif self.is_out_of_stock:
            # Check if the product should no longer appear in listings
            if self.out_of_stock_date and (now() - self.out_of_stock_date).days > 10:
                self.is_visible_in_listing = False  # Make invisible after 10 days
        else:
            # If in stock, ensure the product is visible
            self.is_out_of_stock = False
            self.is_visible_in_listing = True

    def save(self, *args, **kwargs):
        """Override save to always update stock status."""
        self.update_stock_status()  # Update stock status without calling save() again
        super().save(*args, **kwargs)  # Call the parent save method to persist changes


    def available_lengths(self):
        """
        Return available lengths for the selected category size (width),
        based on the defined sizes and sleeve lengths in CategorySize.
        """
        if self.category_size:
            return {
                "size_L_full_length": self.category_size.size_L_full_length,
                "size_L_half_length": self.category_size.size_L_half_length,
                "size_XL_full_length": self.category_size.size_XL_full_length,
                "size_XL_half_length": self.category_size.size_XL_half_length,
                "size_XXL_full_length": self.category_size.size_XXL_full_length,
                "size_XXL_half_length": self.category_size.size_XXL_half_length,
                "size_XXXL_full_length": self.category_size.size_XXXL_full_length,
                "size_XXXL_half_length": self.category_size.size_XXXL_half_length,
            }
        return {}

    def get_length(self, size, sleeve):
        # Assuming that you have a relationship to CategorySize or similar logic for size and sleeve
        category_size = self.category.sizes.filter(width=self.width).first()
        if category_size:
            return category_size.get_length(size, sleeve)
        return None

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/images/')

    def __str__(self):
        return f"Image for {self.product.name}"
