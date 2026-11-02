"""Autorización centralizada para módulos actuales y futuros."""

from django.utils import timezone

from .models import RolePermission, TemporaryAssignment


def _role_queryset(user):
    return user.role_assignments.filter(
        active=True,
        role__active=True,
    ).select_related('role')


def is_system_admin(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'role', None) == 'admin':
        return True
    return _role_queryset(user).filter(role__is_system_role=True).exists()


def has_permission(user, code):
    """Comprueba `module.action`; el administrador tiene acceso futuro total."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if is_system_admin(user):
        return True
    try:
        module, action = code.split('.', 1)
    except ValueError:
        return False
    return RolePermission.objects.filter(
        role__user_assignments__user=user,
        role__user_assignments__active=True,
        role__active=True,
        permission__module=module,
        permission__action=action,
        permission__active=True,
    ).exists()


def has_temporary_function(user, function_code, at=None):
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    moment = at or timezone.now()
    return TemporaryAssignment.objects.filter(
        user=user,
        function__code=function_code,
        function__active=True,
        status='active',
        starts_at__lte=moment,
        ends_at__gte=moment,
    ).exists()


def can_register_external_sale(user, at=None):
    return has_temporary_function(user, 'external_seller', at=at)
