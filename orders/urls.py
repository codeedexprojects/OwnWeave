from django.urls import path
from .views import ActiveAndPastOrdersView,DirectOrderView, ListOrdersView, CheckoutView,OrderUpdateView,ReturnOrderListView,PaymentDetailsListView,OrderDetailView,AdminOrderCreateView,\
            AdminOrderListAPIView,AdminOrderUpdateAPIView,ValidateStockAndOfferView,OrderCountView

urlpatterns = [
    path('', ListOrdersView.as_view(), name='list-order'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),  # Retrieve, update, or delete a specific order
    path('direct-order/', DirectOrderView.as_view(), name='direct-order'),  # Direct order placement
    path('checkout/', CheckoutView.as_view(), name='checkout'),  # Checkout view for address and payment option
    path('orders/<int:pk>/update/', OrderUpdateView.as_view(), name='order-update'),  # ORDER UPDATE NEW
    path('orders/returns/', ReturnOrderListView.as_view(), name='return-orders'), #GET RETURN PRODUCTS
    path('orders/payment-details/', PaymentDetailsListView.as_view(), name='payment-details'), #PAYMENT DETAILS
    path('admin/orders/', AdminOrderCreateView.as_view(), name='admin-order-create'),
    path('admin-orders/list/', AdminOrderListAPIView.as_view(), name='admin-order-list'),
    path('admin-orders/<int:pk>/', AdminOrderUpdateAPIView.as_view(), name='admin-order-update'),
    path('validate-stock-offer/', ValidateStockAndOfferView.as_view(), name='validate-stock-offer'),
    path('orders/active-past/', ActiveAndPastOrdersView.as_view(), name='active_and_past_orders'),
    path('order-count/', OrderCountView.as_view(), name='order-count'),


]
