from decimal import Decimal
from django.conf import settings
from django.forms import ValidationError
import razorpay
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Order, OrderItem, TemporaryOrder
from .serializers import OrderSerializer,PaymentDetailsSerializer,AdminOrderSerializer
from cart.models import Cart
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from products.models import CategorySize, Product
from accounts.models import Address
from collections import defaultdict
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework import generics
from .models import AdminOrder
from rest_framework.exceptions import NotFound
from decimal import Decimal, ROUND_DOWN
from django.db import models


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

def validate_stock_length(product, order_length, quantity):
    """
    Validates if the product has sufficient stock length for the given order.
    """
    total_order_length = order_length * quantity
    if product.stock_length < total_order_length:
        raise ValidationError({"error": f"Insufficient stock for {product.name}"})
    return True

def get_free_products(product, order_length, quantity):
    """
    Retrieves free products eligible for a BOGO offer.
    """
    free_product_length = order_length * quantity
    free_products = Product.objects.filter(
        category=product.category,
        is_out_of_stock=False,
        stock_length__gte=free_product_length
    ).exclude(id=product.id)
    return free_products

class ValidateStockAndOfferView(APIView):
    """
    API endpoint to validate stock length and automatically handle BOGO offers.
    """

    def post(self, request):
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = request.data.get('quantity', 1)

        # Ensure all required fields are present
        if not product_id or not quantity:
            return Response({"error": "Product ID and quantity are required."}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, id=product_id)

        # Calculate order length based on size/sleeve or custom length
        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            if not category_size:
                return Response({"error": "No matching category size found."}, status=status.HTTP_400_BAD_REQUEST)
            order_length = category_size.get_length(size, sleeve)
        elif custom_length:
            try:
                order_length = Decimal(custom_length)
            except ValueError:
                return Response({"error": "Invalid custom length."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not order_length:
            return Response({"error": "Invalid length selection."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate stock length
        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Check for BOGO offer
        if product.offer and product.offer.offer_type == 'BOGO':
            free_products = get_free_products(product, order_length, int(quantity))
            if free_products.exists():
                # Return available free products for selection
                free_products_data = [
                    {
                        "id": free_product.id,
                        "name": free_product.name,
                        "free_product_image": free_product.images.first().image.url if free_product.images.exists() else None,
                        "stock_length": str(free_product.stock_length),
                        "offer_price_per_meter": str(free_product.offer_price_per_meter),
                    }
                    for free_product in free_products
                ]
                return Response({
                    "message": "Stock is sufficient, and BOGO offer is applicable.",
                    "free_products": free_products_data,
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Stock is sufficient, but no free products available for the BOGO offer."
                }, status=status.HTTP_200_OK)

        # If no BOGO offer applies, just return a success response
        return Response({"message": "Stock is sufficient, and no BOGO offer applies."}, status=status.HTTP_200_OK)

class DirectOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))
        offer_product_id = request.data.get('offer_product_id')

        product = get_object_or_404(Product, id=product_id)

        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            if not category_size:
                return Response({"error": "No matching category size found."}, status=status.HTTP_400_BAD_REQUEST)
            length = category_size.get_length(size, sleeve)
        elif custom_length:
            length = Decimal(custom_length)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not length:
            return Response({"error": "Invalid length selection."}, status=status.HTTP_400_BAD_REQUEST)

        total_price = Decimal(product.offer_price_per_meter) * length * quantity
        offer_type = None
        discount_amount = Decimal("0.00")

        if product.offer:
            if product.offer.offer_type == 'BOGO':
                free_product = offer_product_id
                if free_product:
                    offer_type = 'BOGO'
                    free_product_id = free_product
                    discount_amount = 0
            elif product.offer.offer_type == 'PERCENTAGE':
                offer_type = 'PERCENTAGE'
                discount_percentage = product.offer.discount_percentage
                discount_amount = total_price * (Decimal(discount_percentage) / 100)
                total_price -= discount_amount

        total_price = max(Decimal("0.00"), total_price)

        # Store the temporary order in the TemporaryOrder model
        temporary_order = TemporaryOrder.objects.create(
            user=user,
            product_id=product.id,
            quantity=quantity,
            size=size,
            sleeve=sleeve,
            custom_length=custom_length,
            length=length,
            price=total_price,
            offer_type=offer_type,
            discount_amount=discount_amount,
            free_product=free_product_id
        )

        return Response({
            "message": "Direct order placed. Proceed to checkout.",
            "temporary_order_id": temporary_order.id
        }, status=status.HTTP_201_CREATED)


    def get(self, request):
        """
        Retrieve the temporary order data stored in the TemporaryOrder model.
        """
        order_id = request.query_params.get('temporary_order_id')
        if not order_id:
            return Response({"error": "Temporary order ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            temporary_order = TemporaryOrder.objects.get(id=order_id)
        except TemporaryOrder.DoesNotExist:
            return Response({"error": "Temporary order not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve main product details
        try:
            main_product = Product.objects.get(id=temporary_order.product_id)
            main_product_name = main_product.name
            main_product_image = main_product.images.first().image.url if main_product.images.exists() else None
        except Product.DoesNotExist:
            return Response({"error": "Main product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve free product details if applicable
        free_product_name = None
        free_product_image = None
        if temporary_order.free_product:
            try:
                free_product = Product.objects.get(id=temporary_order.free_product)
                free_product_name = free_product.name
                free_product_image = free_product.images.first().image.url if free_product.images.exists() else None
            except Product.DoesNotExist:
                pass

        # Prepare response data
        return Response({
            "message": "Temporary order data retrieved successfully.",
            "order_item": {
                "main_product": {
                    "id": main_product.id,
                    "name": main_product_name,
                    "image": main_product_image,
                    "quantity": temporary_order.quantity,
                    "size": temporary_order.size,
                    "sleeve": temporary_order.sleeve,
                    "custom_length": temporary_order.custom_length,
                    "length": str(temporary_order.length),
                    "price": str(temporary_order.price),
                    "offer_type": temporary_order.offer_type,
                    "discount_amount": str(temporary_order.discount_amount),
                },
                "free_product": {
                    "id": temporary_order.free_product,
                    "name": free_product_name,
                    "image": free_product_image,
                    "quantity": temporary_order.quantity,  # Same as main product
                    "size": temporary_order.size,        # Same as main product
                    "sleeve": temporary_order.sleeve,    # Same as main product
                    "custom_length": temporary_order.custom_length  # Same as main product
                }
            }
        }, status=status.HTTP_200_OK)




class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        temporary_order_id = request.data.get('temporary_order_id')

        # Retrieve the temporary order
        try:
            temporary_order = TemporaryOrder.objects.get(id=temporary_order_id, user=user)
        except TemporaryOrder.DoesNotExist:
            return Response({"error": "No temporary order found."}, status=status.HTTP_400_BAD_REQUEST)

        address_id = request.data.get('address_id')
        payment_option = request.data.get('payment_option')
        address = get_object_or_404(Address, id=address_id, user=user)

        product_price = temporary_order.price
        discount_amount = temporary_order.discount_amount
        final_total = product_price - discount_amount
        final_total = max(Decimal("0.00"), final_total)

        if payment_option == 'Razorpay':
            razorpay_order = razorpay_client.order.create({
                "amount": int(final_total * 100),
                "currency": "INR",
                "payment_capture": "1"
            })
            return Response({
                "razorpay_order_id": razorpay_order['id'],
                "amount": final_total,
                "currency": "INR"
            }, status=status.HTTP_200_OK)

        elif payment_option == 'COD':
            order = self.create_order(user, address, final_total, temporary_order, payment_option)
            serializer = OrderSerializer(order)
            # Delete the temporary order after checkout
            temporary_order.delete()
            return Response({
                "message": "Order placed successfully with COD.",
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid payment option."}, status=status.HTTP_400_BAD_REQUEST)

    def create_order(self, user, address, total_price, temporary_order, payment_option):
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            status='pending',
            shipping_address=address,
            payment_option=payment_option
        )

        product = get_object_or_404(Product, id=temporary_order.product_id)
        ordered_length = temporary_order.length * temporary_order.quantity
        if product.stock_length < ordered_length:
            raise ValidationError({"error": f"Insufficient stock for {product.name}"})

        product.stock_length -= ordered_length
        product.save()

        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=temporary_order.quantity,
            size=temporary_order.size,
            sleeve=temporary_order.sleeve,
            custom_length=temporary_order.custom_length,
            length=ordered_length,
            price=temporary_order.price
        )

        if temporary_order.free_product:
            free_product = get_object_or_404(Product, id=temporary_order.free_product)
            free_product_length = temporary_order.length * temporary_order.quantity
            if free_product.stock_length < free_product_length:
                raise ValidationError({"error": f"Insufficient stock for free product {free_product.name}"})

            free_product.stock_length -= free_product_length
            free_product.save()

            OrderItem.objects.create(
                order=order,
                product=free_product,
                quantity=temporary_order.quantity,
                custom_length=temporary_order.custom_length,
                length=ordered_length,
                price=0
            )

        return order




class ListOrdersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this endpoint
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        Return a list of orders based on the user's role.
        Admin and staff can view all orders, while regular users can only view their own orders.
        """
        user = self.request.user

        if user.is_staff or user.is_superuser:
            # Admins and staff can view all orders
            return Order.objects.all()

        # Regular users can only view their own orders
        return Order.objects.filter(user=user)

    def get(self, request, *args, **kwargs):
        """
        List all orders for admin/staff or only user's orders for regular users.
        """
        orders = self.get_queryset()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActiveAndPastOrdersView(generics.ListAPIView):
    """
    API view to list active and past (completed) orders based on order status.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return active or past orders based on a query parameter.
        Active orders are orders not yet completed.
        Past orders are completed orders.
        """
        user = self.request.user
        status_filter = self.request.query_params.get('status', 'active')  # Default to active orders

        if user.is_staff or user.is_superuser:
            # Admin/staff can view all orders
            queryset = Order.objects.all()
        else:
            # Regular users can only view their own orders
            queryset = Order.objects.filter(user=user)

        if status_filter == 'active':
            # Filter for active orders (exclude completed orders)
            queryset = queryset.exclude(status=Order.OrderStatus.COMPLETED)
        elif status_filter == 'past':
            # Filter for past (completed) orders
            queryset = queryset.filter(status=Order.OrderStatus.COMPLETED)

        return queryset.order_by('-id')

    def get(self, request, *args, **kwargs):
        """
        Return a list of active or past orders.
        Use 'status=active' or 'status=past' as query parameters.
        """
        orders = self.get_queryset()
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Admin and staff users can access all orders.
        Regular users can only access their own orders.
        """
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all()  # Admin/staff can view any order
        return Order.objects.filter(user=user)  # Regular users can only view their own orders

    def get(self, request, *args, **kwargs):
        """
        Retrieve a specific order.
        """
        order = self.get_object()
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """
        Update a specific order.
        """
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """
        Delete a specific order.
        """
        order = self.get_object()
        order.delete()
        return Response({"detail": "Order deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class OrderUpdateView(RetrieveUpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)  # Determine if it's a partial update
        instance = self.get_object()  # Retrieve the specific order instance
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()  # Save updated order details
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReturnOrderListView(generics.ListAPIView):
    """
    API view to list all orders with status 'RETURN'.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(status=Order.OrderStatus.RETURN)

class PaymentDetailsListView(generics.ListAPIView):
    """
    API view to list payment details from the Order model.
    """
    serializer_class = PaymentDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.all()


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access this endpoint
    queryset = Order.objects.all()  # Retrieve all orders (will filter for the correct order)
    serializer_class = OrderSerializer

    def get_object(self):
        """
        Override the get_object method to ensure users can only access their own orders,
        or admins and staff can access any order.
        """
        user = self.request.user
        order = self.get_queryset().filter(id=self.kwargs['pk'])

        if user.is_staff or user.is_superuser:
            # Admin and staff can view any order
            return order.first()  # Assuming `id` is unique, use `first()` to return a single object
        else:
            # Regular users can only view their own order
            return order.filter(user=user).first()

class AdminOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Step 1: Collect and validate customer data
        customer_data = {
            'name': request.data.get('name'),
            'phoneNumber': request.data.get('phoneNumber'),
            'address': request.data.get('address'),
            'state': request.data.get('state'),
            'pincode': request.data.get('pincode'),
            'city': request.data.get('city'),
            'district': request.data.get('district'),
        }

        # Check if all required customer data is provided
        for key, value in customer_data.items():
            if not value:
                return Response({"error": f"{key} is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Extract product data
        product_code = request.data.get('product_code')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))  # Default quantity is 1

        # Get the main product
        product = get_object_or_404(Product, product_code=product_code)

        # Step 3: Determine product length (based on size/sleeve or custom length)
        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            if not category_size:
                return Response({"error": "No matching category size found."}, status=status.HTTP_400_BAD_REQUEST)
            length = category_size.get_length(size, sleeve)
        elif custom_length:
            length = Decimal(custom_length)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not length:
            return Response({"error": "Invalid length selection."}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Calculate total price (before offers)
        total_price = Decimal(product.offer_price_per_meter) * length * quantity
        total_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        # Step 5: Handle offers (including BOGO)
        discount_amount = Decimal("0.00")
        free_product = None  # Free product for BOGO
        free_product_length = Decimal("0.00")
        if product.offer:
            if product.offer.offer_type == 'PERCENTAGE':
                discount_percentage = product.offer.discount_value
                discount_amount = total_price * (Decimal(discount_percentage) / 100)
                total_price -= discount_amount
                total_price = total_price.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            elif product.offer.offer_type == 'BOGO':
                free_product = product  # The free product is the same as the main product
                free_product_length = length * quantity  # Length for the free product

        # Step 6: Validate stock for the main product
        ordered_length = length * quantity
        if product.stock_length < ordered_length:
            raise ValidationError({"error": f"Insufficient stock for {product.name}"})

        # Deduct stock for the main product
        product.stock_length -= ordered_length
        product.save()

        # Step 7: Validate and deduct stock for the free product (if BOGO offer applies)
        if free_product:
            if free_product.stock_length < free_product_length:
                raise ValidationError({"error": f"Insufficient stock for free product {free_product.name}"})

            free_product.stock_length -= free_product_length
            free_product.save()

        # Step 8: Prepare the order data for the main product
        order_data = {
            'name': customer_data['name'],
            'phoneNumber': customer_data['phoneNumber'],
            'address': customer_data['address'],
            'state': customer_data['state'],
            'pincode': customer_data['pincode'],
            'city': customer_data['city'],
            'district': customer_data['district'],
            'productCode': product.id,  # Save the product as the productCode FK
            'size': size,
            'customSize': custom_length,
            'quantity': quantity,
            'paymentMethod': request.data.get('paymentMethod'),
            'paymentStatus': request.data.get('paymentStatus'),
            'sleeveType': sleeve,
            'total_price': total_price
        }

        # Step 9: Serialize and save the order for the main product
        serializer = AdminOrderSerializer(data=order_data)
        if serializer.is_valid():
            order = serializer.save()

            # If a free product exists (BOGO), create an additional order item for the free product
            if free_product:
                free_order_data = {
                    'name': order.name,
                    'phoneNumber': order.phoneNumber,
                    'address': order.address,
                    'state': order.state,
                    'pincode': order.pincode,
                    'city': order.city,
                    'district': order.district,
                    'productCode': free_product.id,  # Save the free product as the productCode FK
                    'size': size,
                    'customSize': custom_length,
                    'quantity': quantity,  # Same quantity for the free product
                    'paymentMethod': order.paymentMethod,
                    'paymentStatus': "Completed",  # The free product will be marked as completed
                    'sleeveType': order.sleeveType,
                    'total_price': Decimal("0.00"),  # Free product has no price
                }
                free_order_serializer = AdminOrderSerializer(data=free_order_data)
                if free_order_serializer.is_valid():
                    free_order_serializer.save()

            # Return the response with the created order data
            return Response({"message": "Order created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class AdminOrderListAPIView(generics.ListAPIView):
    queryset = AdminOrder.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filter the queryset based on some query parameters, for example:
        - Filter by `product_code`
        - Filter by `status`
        """
        queryset = super().get_queryset()

        # Filter by product_code if provided in query params
        product_code = self.request.query_params.get('product_code', None)
        if product_code:
            queryset = queryset.filter(product_code=product_code)

        # Example filter by payment status
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(paymentStatus=payment_status)

        return queryset

class AdminOrderUpdateAPIView(generics.UpdateAPIView):
    queryset = AdminOrder.objects.all()
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        """
        Override the get_object method to get the AdminOrder by its ID.
        Raise a NotFound exception if the object doesn't exist.
        """
        try:
            order_id = self.kwargs.get('pk')
            return AdminOrder.objects.get(pk=order_id)
        except AdminOrder.DoesNotExist:
            raise NotFound(detail="Order not found.")

    def perform_update(self, serializer):
        """
        Override perform_update to save the updated data after validation.
        """
        serializer.save()

class OrderCountView(APIView):
    """
    API to get the total count of orders placed, including order status-wise breakdown.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Return the total count of orders and a breakdown by order status.
        """
        user = request.user
        if user.is_staff or user.is_superuser:
            orders = Order.objects.all()
        else:
            orders = Order.objects.filter(user=user)
        total_orders = orders.count()
        status_counts = orders.values('status').annotate(count=models.Count('id'))
        status_counts_dict = {item['status']: item['count'] for item in status_counts}
        return Response({
            "total_orders": total_orders,
            "status_counts": status_counts_dict,
        }, status=status.HTTP_200_OK)