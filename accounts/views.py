from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from accounts.permissions import IsAdminOrStaff
from .models import Address, CustomUser
from .serializers import (
    CreateStaffUserSerializer,
    UserAdminSerializer,
    UserLoginSerializer,
    UserSerializer,
    AddressSerializer
)
from rest_framework.exceptions import NotFound


class CustomerListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(is_staff=False, is_superuser=False)
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminOrStaff]

class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.filter(is_staff=False, is_superuser=False)
    serializer_class = UserAdminSerializer
    permission_classes = [IsAdminOrStaff]
    lookup_field = 'mobile_number'

class AdminUpdateAddressView(APIView):
    permission_classes = [IsAdminOrStaff]

    def put(self, request, mobile_number):
        return self.update_address(request, mobile_number, partial=False)

    def patch(self, request, mobile_number):
        return self.update_address(request, mobile_number, partial=True)

    def update_address(self, request, mobile_number, partial):
        address_id = request.data.get('address_id')

        try:
            # Fetch the address associated with the user
            address = Address.objects.get(id=address_id, user__mobile_number=mobile_number)
        except Address.DoesNotExist:
            return Response({"detail": "Address not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AddressSerializer(address, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# User registration with JWT token and pincode details retrieval
class UserRegistrationView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Prepare the response with token and user data
        detailed_response = {
            'message': 'Registration successful',
            'user': {
                'name': user.name,
                'mobile_number': user.mobile_number,
                'email': user.email,
                'address': user.addresses.first().address if user.addresses.exists() else None,
                'post_office': user.addresses.first().post_office if user.addresses.exists() else None,
                'block': user.addresses.first().block if user.addresses.exists() else None,
                'district': user.addresses.first().district if user.addresses.exists() else None,
                'state': user.addresses.first().state if user.addresses.exists() else None,
                'country': user.addresses.first().country if user.addresses.exists() else None,
                'is_home': user.addresses.first().is_home if user.addresses.exists() else None,
                'is_office': user.addresses.first().is_office if user.addresses.exists() else None,
                'is_other': user.addresses.first().is_other if user.addresses.exists() else None,
                'is_default': user.addresses.first().is_default if user.addresses.exists() else None,
            },
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }

        return Response(detailed_response, status=status.HTTP_201_CREATED)



# Customer login view with JWT token authentication
class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Fetch the user based on the mobile number
        user = get_object_or_404(CustomUser, mobile_number=serializer.validated_data['mobile_number'], is_staff=False, is_superuser=False)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Customer login successful',
            'username': user.name,
            'mobile_number': user.mobile_number,
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


# Admin/staff login view with JWT token authentication
class AdminStaffLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_object_or_404(CustomUser, mobile_number=serializer.validated_data['mobile_number'], is_staff=True)

        if not user.check_password(serializer.validated_data['password']):
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'message': 'Admin/staff login successful',
            'username': user.name,
            'mobile_number': user.mobile_number,
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)


# Logout view
class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Attempt to blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Invalid token or token not provided"}, status=status.HTTP_400_BAD_REQUEST)


# Retrieve current user details and all addresses
class UserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get all addresses of the user
        addresses = user.addresses.all()

        # Serialize the addresses
        address_data = AddressSerializer(addresses, many=True).data

        return Response({
            'username': user.name,
            'mobile_number': user.mobile_number,
            'addresses': address_data,
        })


# Update user's default address
class UserUpdateView(generics.UpdateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Fetch the default address of the authenticated user
        return self.request.user.addresses.get(is_default=True)

    def update(self, request, *args, **kwargs):
        # Allow partial updates without enforcing all required fields
        mutable_data = request.data.copy()

        # Create a partial serializer that allows for optional fields
        serializer = self.get_serializer(self.get_object(), data=mutable_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


# Create staff user (Admin-only)
class CreateStaffView(generics.CreateAPIView):
    serializer_class = CreateStaffUserSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AddAddressView(generics.CreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Associate the new address with the current user
        serializer.save(user=self.request.user)

class RetrieveAddressView(generics.RetrieveAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ensure that only addresses belonging to the authenticated user are retrieved
        return self.queryset.filter(user=self.request.user)

# class UpdateAddressView(generics.UpdateAPIView):
#     permission_classes = [IsAuthenticated]
#     serializer_class = AddressSerializer

#     def get_queryset(self):
#         # Restrict to the authenticated user's addresses
#         return Address.objects.filter(user=self.request.user)

#     def get_object(self):
#         queryset = self.get_queryset()
#         address_id = self.kwargs.get('pk')  # Extract address ID from the URL
#         try:
#             return queryset.get(pk=address_id)
#         except Address.DoesNotExist:
#             raise NotFound("The requested address does not exist or is not accessible.")

class UpdateAddressView(generics.UpdateAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ensure users can only update their own addresses
        return Address.objects.filter(user=self.request.user)

class DeleteAddressView(generics.DestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Limit to addresses owned by the authenticated user
        return Address.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'message': 'Address deleted successfully.'}, status=status.HTTP_200_OK)