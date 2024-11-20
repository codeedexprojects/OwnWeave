from django.urls import path
from .views import CartView, CheckoutCartView, SelectAddressView

urlpatterns = [
    # URL to view the cart and its items
    path('', CartView.as_view(), name='cart-view'),

    # URL to add an item to the cart
    path('add/', CartView.as_view(), name='cart-add'),

    # URL to delete an item from the cart (by item_id)
    path('remove/<int:item_id>/', CartView.as_view(), name='cart-remove'),

    # URL to clear all items in the cart
    path('clear/', CartView.as_view(), name='cart-clear'),

    # URL to update a specific item in the cart (replace entire item with PUT)
    path('update/<int:item_id>/', CartView.as_view(), name='cart-update'),

    # URL to partially update a cart item (e.g., update quantity) with PATCH
    path('partial-update/<int:item_id>/', CartView.as_view(), name='cart-partial-update'),

    # Checkout view
    path('checkout/', CheckoutCartView.as_view(), name='checkout-cart'),  # POST to checkout
    path('addresses/', SelectAddressView.as_view(), name='select-address'),  # GET user's addresses
]
