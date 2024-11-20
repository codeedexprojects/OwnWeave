from decimal import Decimal
import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from accounts.models import Address
from accounts.serializers import AddressSerializer
from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from orders.views import validate_stock_length
from products.models import Product
from .models import Cart, CartItem
from .serializers import CartSerializer


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the current user's cart and its items."""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Add an item to the cart with validations for stock and offers."""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))
        offer_product_id = request.data.get('offer_product_id')

        product = get_object_or_404(Product, id=product_id)

        # Validate stock length
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

        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Calculate price
        length = order_length
        price = Decimal(product.offer_price_per_meter) * length
        discount_amount = Decimal("0.00")
        offer_type = None

        # Handle offers
        if product.offer:
            if product.offer.offer_type == 'BOGO':
                free_product = offer_product_id
                if free_product:
                    offer_type = 'BOGO'
                    free_product_id = free_product
                    discount_amount = 0  # No discount on the main product, but BOGO applies
                    # Create cart item for the free product
                    CartItem.objects.create(
                        cart=cart,
                        product=free_product_id,
                        quantity=quantity,
                        size=size,
                        sleeve=sleeve,
                        custom_length=custom_length,
                        length=length,
                        price=0,  # Free product, so no cost
                        discount_amount=0,
                        offer_type='BOGO',
                    )
            elif product.offer.offer_type == 'PERCENTAGE':
                offer_type = 'PERCENTAGE'
                discount_percentage = product.offer.discount_percentage
                discount_amount = price * (Decimal(discount_percentage) / 100)

        # Add or update the cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'size': size,
                'sleeve': sleeve,
                'custom_length': custom_length,
                'length': length,
                'price': price - discount_amount,
                'discount_amount': discount_amount,
                'offer_type': offer_type,
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response({"message": "Item added to cart"}, status=status.HTTP_200_OK)

    def delete(self, request, item_id):
        """Remove a specific item from the cart."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        return Response({"message": "Item removed from cart"}, status=status.HTTP_200_OK)

    def delete_all(self, request):
        """Clear all items from the cart."""
        cart = get_object_or_404(Cart, user=request.user)
        cart.items.all().delete()
        return Response({"message": "Cart cleared"}, status=status.HTTP_200_OK)


    def put(self, request, item_id):
        """Edit an existing cart item (replace the item)."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        # Get the new details from the request
        product_id = request.data.get('product_id')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')
        quantity = int(request.data.get('quantity', 1))
        offer_product_id = request.data.get('offer_product_id')

        product = get_object_or_404(Product, id=product_id)

        # Validate stock length
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

        try:
            validate_stock_length(product, order_length, quantity)
        except ValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Calculate price
        length = order_length
        price = Decimal(product.offer_price_per_meter) * length
        discount_amount = Decimal("0.00")
        offer_type = None

        # Handle offers
        if product.offer:
            if product.offer.offer_type == 'BOGO':
                free_product = offer_product_id
                if free_product:
                    offer_type = 'BOGO'
                    free_product_id = free_product
                    discount_amount = 0  # No discount on the main product, but BOGO applies
                    # Create cart item for the free product
                    CartItem.objects.create(
                        cart=cart,
                        product=free_product_id,
                        quantity=quantity,
                        size=size,
                        sleeve=sleeve,
                        custom_length=custom_length,
                        length=length,
                        price=0,  # Free product, so no cost
                        discount_amount=0,
                        offer_type='BOGO',
                    )
            elif product.offer.offer_type == 'PERCENTAGE':
                offer_type = 'PERCENTAGE'
                discount_percentage = product.offer.discount_percentage
                discount_amount = price * (Decimal(discount_percentage) / 100)

        # Update the cart item
        cart_item.product = product
        cart_item.size = size
        cart_item.sleeve = sleeve
        cart_item.custom_length = custom_length
        cart_item.quantity = quantity
        cart_item.length = length
        cart_item.price = price - discount_amount
        cart_item.discount_amount = discount_amount
        cart_item.offer_type = offer_type
        cart_item.save()

        return Response({"message": "Cart item updated successfully."}, status=status.HTTP_200_OK)

    def patch(self, request, item_id):
        """Partially update a cart item (e.g., update quantity, size, etc.)."""
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        # Update only the provided fields
        quantity = request.data.get('quantity')
        size = request.data.get('size')
        sleeve = request.data.get('sleeve')
        custom_length = request.data.get('custom_length')


        if quantity:
            cart_item.quantity = quantity
        if size:
            cart_item.size = size
        if sleeve:
            cart_item.sleeve = sleeve
        if custom_length:
            cart_item.custom_length = custom_length

        # Recalculate the price based on updated fields
        product = cart_item.product
        if size and sleeve:
            category_size = product.category.sizes.filter(width=product.width).first()
            order_length = category_size.get_length(size, sleeve)
        elif custom_length:
            order_length = Decimal(custom_length)
        else:
            return Response({"error": "Either size/sleeve or custom length is required."}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.length = order_length
        price = Decimal(product.offer_price_per_meter) * order_length
        cart_item.price = price - cart_item.discount_amount

        cart_item.save()
        return Response({"message": "Cart item updated successfully."}, status=status.HTTP_200_OK)



class CheckoutCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Checkout the cart and create an order."""
        user = request.user
        cart = get_object_or_404(Cart, user=user)

        if not cart.items.exists():
            return Response({"error": "Cart is empty. Add items before checkout."}, status=status.HTTP_400_BAD_REQUEST)

        address_id = request.data.get('address_id')
        payment_option = request.data.get('payment_option')
        address = get_object_or_404(Address, id=address_id, user=user)

        # Calculate total price
        total_price = Decimal("0.00")
        for item in cart.items.all():
            total_price += item.price * item.quantity

            # Validate stock for each item
            try:
                validate_stock_length(item.product, item.length, item.quantity)
            except ValidationError as e:
                return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # Handle payment
        if payment_option == 'Razorpay':
            razorpay_order = razorpay_client.order.create({
                "amount": int(total_price * 100),
                "currency": "INR",
                "payment_capture": "1"
            })
            return Response({
                "razorpay_order_id": razorpay_order['id'],
                "amount": str(total_price),
                "currency": "INR"
            }, status=status.HTTP_200_OK)

        elif payment_option == 'COD':
            order = self.create_order(user, address, total_price, cart, payment_option)
            serializer = OrderSerializer(order)
            return Response({
                "message": "Order placed successfully with COD.",
                "order": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Invalid payment option."}, status=status.HTTP_400_BAD_REQUEST)

    def create_order(self, user, address, total_price, cart, payment_option):
        """Helper function to create an order."""
        order = Order.objects.create(
            user=user,
            total_price=total_price,
            shipping_address=address,
            payment_option=payment_option
        )

        for item in cart.items.all():
            # Deduct stock
            item.product.stock_length -= item.length * item.quantity
            item.product.save()

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                size=item.size,
                sleeve=item.sleeve,
                custom_length=item.custom_length,
                length=item.length,
                price=item.price
            )

        # Clear the cart after creating the order
        cart.items.all().delete()
        return order



class SelectAddressView(ListAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all addresses for the logged-in user
        return Address.objects.filter(user=self.request.user)