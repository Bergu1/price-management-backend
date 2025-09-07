# app/products/permissions.py
from rest_framework.permissions import BasePermission

class IsEmployee(BasePermission):
    """
    Dostęp tylko dla zalogowanych pracowników do WSZYSTKICH metod (GET/POST/PATCH/DELETE).
    """
    message = "Only employees may access this endpoint."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, "is_employee", False))
