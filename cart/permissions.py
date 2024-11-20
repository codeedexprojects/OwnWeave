# cart/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        # Allow full access for admin and staff
        return request.user.is_staff or request.user.is_superuser

class IsCartOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow full access to admin and staff, restrict users to their own carts
        if request.user.is_staff or request.user.is_superuser:
            return True
        # Allow read-only access for non-owners
        if request.method in SAFE_METHODS:
            return True
        # Check if the user is the owner of the cart item for other actions
        return obj.user == request.user
