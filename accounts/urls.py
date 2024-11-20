from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import (
    AddAddressView,
    AdminUpdateAddressView,
    CustomerDetailView,
    CustomerListView,
    DeleteAddressView,
    RetrieveAddressView,
    UpdateAddressView,
    UserRegistrationView,
    UserLoginView,
    AdminStaffLoginView,
    UserUpdateView,
    UserLogoutView,
    UserDetailView,
    CreateStaffView,
)


urlpatterns = [
    # Registration and Login
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('admin-staff-login/', AdminStaffLoginView.as_view(), name='admin-staff-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User Management
    path('update/', UserUpdateView.as_view(), name='user-update'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('add-address/', AddAddressView.as_view(), name='add_address'),
    path('update-address/<int:pk>/', UpdateAddressView.as_view(), name='update-address'),
    path('address/<int:pk>/', RetrieveAddressView.as_view(), name='retrieve-address'),
    path('delete-address/<int:pk>/', DeleteAddressView.as_view(), name='delete-address'),



    # Admin-only Management
    # Customer management by admin/staff
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('customers/<str:mobile_number>/', CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<str:mobile_number>/update-address/', AdminUpdateAddressView.as_view(), name='customer-update-address'),
    path('create-staff/', CreateStaffView.as_view(), name='create_staff'),
]
