from rest_framework.permissions import BasePermission

class IsAdminOrStaff(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is authenticated and is either staff or superuser
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)
