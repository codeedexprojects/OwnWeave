from django.db import models
from django.conf import settings
from accounts.models import Address
from products.models import Product, CategorySize

class Order(models.Model):
    class PaymentOptions(models.TextChoices):
        COD = 'COD', 'Cash on Delivery'
        RAZORPAY = 'Razorpay', 'Online Payment'

    class PaymentStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        FAILED = 'Failed', 'Failed'

    class ReturnStatus(models.TextChoices):
        RETURN_INITIATED = 'Return Initiated','Return Initiated'
        PENDING = 'Pending','Pending'
        COMPLETED = 'Completed','Completed'

    class OrderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPT = 'Accept','Accept'
        REJECT = 'Reject','Reject'
        RETURN = 'Return','Return'
        COMPLETED = 'Completed','Completed'
        # PROCESSING = 'processing', 'Processing'
        # SHIPPED = 'shipped', 'Shipped'
        # DELIVERED = 'delivered', 'Delivered'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    Track_id = models.CharField(max_length=200,null=True,blank=True)
    return_status = models.CharField(max_length=20, choices=ReturnStatus.choices,null=True,blank=True)
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL,null=True)
    payment_option = models.CharField(max_length=10, choices=PaymentOptions.choices)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} for {self.user}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=6, null=True, blank=True, choices=CategorySize.SIZE_CHOICES, help_text="Select size (L, XL, XXL, etc.)")
    sleeve = models.CharField(max_length=10, null=True, blank=True, choices=CategorySize.SLEEVE_CHOICES, help_text="Select sleeve type (full, half, etc.)")
    custom_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    free_product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_item_free_product")

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.size}, {self.sleeve})"

class TemporaryOrder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product_id = models.PositiveIntegerField()  # Reference to the product
    quantity = models.PositiveIntegerField()
    size = models.CharField(max_length=6, null=True, blank=True)
    sleeve = models.CharField(max_length=10, null=True, blank=True)
    custom_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offer_type = models.CharField(max_length=20, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_product = models.PositiveIntegerField(null=True, blank=True)  # If there's a free product (reference to product ID)

    def __str__(self):
        return f"Temporary order for {self.user} on product {self.product_id}"


class AdminOrder(models.Model):
    name = models.CharField(max_length=255)
    phoneNumber = models.CharField(max_length=15)
    address = models.TextField()
    state = models.CharField(max_length=255)
    pincode = models.CharField(max_length=10)
    city = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    productCode = models.ForeignKey(Product, on_delete=models.CASCADE,related_name='admin_orders')
    size = models.CharField(max_length=50, null=True, blank=True)
    customSize = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    paymentMethod = models.CharField(max_length=50, choices=[('COD', 'Cash on Delivery'), ('Online', 'Online')])
    paymentStatus = models.CharField(max_length=50, choices=[('Pending', 'Pending'), ('Completed', 'Completed')])
    sleeveType = models.CharField(max_length=50, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"Order for {self.name} - {self.product.name}"

