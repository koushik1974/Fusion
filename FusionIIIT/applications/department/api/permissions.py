"""Permission helpers for the department API.

These permission classes are intentionally reusable so view modules can compose
role checks without repeating designation parsing logic.
"""

from rest_framework.permissions import BasePermission


def _get_designation_tokens(user):
    """Return normalized designation names and full_names for the given user."""
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if not hasattr(user, "holds_designations"):
        return []

    names = list(
        user.holds_designations.select_related("designation").values_list(
            "designation__name", flat=True
        )
    )
    full_names = list(
        user.holds_designations.select_related("designation").values_list(
            "designation__full_name", flat=True
        )
    )

    return [str(value).strip().lower() for value in (names + full_names) if value]


def has_any_designation(user, tokens):
    """Return True when any token appears in a user's designation values."""
    normalized = _get_designation_tokens(user)
    for name in normalized:
        for token in tokens:
            token = str(token).strip().lower()
            if token and token in name:
                return True
    return False


class AllowAuthenticated(BasePermission):
    """Allow access only to authenticated users."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsDepartmentAdmin(BasePermission):
    """Allow only department admins."""

    def has_permission(self, request, view):
        return has_any_designation(request.user, ["deptadmin", "dept_admin"])


class IsHOD(BasePermission):
    """Allow only HOD designations."""

    def has_permission(self, request, view):
        tokens = _get_designation_tokens(request.user)
        return any(name.startswith("hod") or "hod" in name for name in tokens)


class IsAssistantProfessor(BasePermission):
    """Allow only assistant professors."""

    def has_permission(self, request, view):
        return has_any_designation(request.user, ["assistant professor"])


class IsDepartmentAdminOrHOD(BasePermission):
    """Allow department admins and HOD users."""

    def has_permission(self, request, view):
        return IsDepartmentAdmin().has_permission(request, view) or IsHOD().has_permission(request, view)
