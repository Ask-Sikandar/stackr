from rest_framework.exceptions import PermissionDenied

from .models import Project


def get_project_for_user(user, project_id: int) -> Project:
    if not user or not user.is_authenticated:
        raise PermissionDenied("Authentication required.")

    project = (
        Project.objects.select_related("organization")
        .filter(
            id=project_id,
            organization__memberships__user=user,
            organization__memberships__is_active=True,
        )
        .first()
    )
    if project is None:
        raise PermissionDenied("Project not found or access denied.")

    return project
