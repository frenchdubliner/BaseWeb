from rest_framework.permissions import BasePermission


class IsVerified(BasePermission):
    """Blocks unverified (is_active=False) users from an endpoint."""

    message = "Please verify your email address before accessing this resource."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsOwnerOrAdmin(BasePermission):
    """Object-level permission: only the owning user or staff/admin may access."""

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return obj == request.user
