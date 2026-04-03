from rest_framework.permissions import BasePermission


class IsDocumentProjectMember(BasePermission):
    """
    Placeholder for future object-level checks.
    API-level queryset filtering currently enforces membership.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
