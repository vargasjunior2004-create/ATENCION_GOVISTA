"""Autorización centralizada para módulos actuales y futuros."""

from django.db.models import Q
from django.utils import timezone

from .models import RolePermission, TemporaryAssignment


PRODUCTIVITY_SUPERVISOR_ROLES = {'gerente', 'jefe-comercial'}


def _role_queryset(user):
    return user.role_assignments.filter(
        active=True,
        role__active=True,
    ).select_related('role')


def is_system_admin(user):
    """Acceso total al sistema.

    No confundir con un rol protegido: Gerente es protegido, pero no
    necesariamente concede acceso total.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'role', None) == 'admin':
        return True
    return _role_queryset(user).filter(role__grants_full_access=True).exists()


def can_supervise_productivity(user):
    """Indica si puede consultar la actividad comercial de todo el equipo."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if is_system_admin(user):
        return True
    return _role_queryset(user).filter(
        role__code__in=PRODUCTIVITY_SUPERVISOR_ROLES,
    ).exists()


def parse_permission_code(code):
    """Devuelve (module, resource, action) desde ``a.b.c`` o ``a.b``."""
    if not code or '.' not in code:
        return None
    path, action = code.rsplit('.', 1)
    if not path or not action:
        return None
    if '.' in path:
        module, resource = path.split('.', 1)
    else:
        module, resource = path, ''
    if not module or not resource and '.' in path:
        return None
    return module, resource, action


def has_permission(user, code):
    """Comprueba un permiso ``module.resource.action`` o ``module.action``.

    El administrador de sistemas tiene acceso futuro total.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if is_system_admin(user):
        return True
    parsed = parse_permission_code(code)
    if not parsed:
        return False
    module, resource, action = parsed
    allowed = RolePermission.objects.filter(
        role__user_assignments__user=user,
        role__user_assignments__active=True,
        role__active=True,
        permission__module=module,
        permission__resource=resource,
        permission__action=action,
        permission__active=True,
    ).exists()
    if allowed:
        return True

    # Compatibility aliases for permissions created before the granular
    # resource segment was introduced.  New callers use the canonical
    # three-part code; existing roles keep working during the transition.
    legacy_module = {
        'auditoria': 'audit',
        'usuarios': 'users',
        'respaldos': 'backups',
    }.get(module, module)
    return RolePermission.objects.filter(
        role__user_assignments__user=user,
        role__user_assignments__active=True,
        role__active=True,
        permission__module=legacy_module,
        permission__resource='',
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


def superadmin_users_qs(User):
    """QuerySet de usuarios activos que conservan acceso total.

    Se incluye el rol legado ``admin`` mientras dure la transición. La
    consulta se usa para impedir dejar el sistema sin administradores.
    """
    return User.objects.filter(active=True).filter(
        Q(role='admin')
        | Q(role_assignments__active=True,
            role_assignments__role__active=True,
            role_assignments__role__grants_full_access=True)
    ).distinct()


def is_last_superadmin(user):
    """True si ``user`` es el único superadministrador activo."""
    return superadmin_users_qs(type(user)).filter(pk=user.pk).exists() \
        and superadmin_users_qs(type(user)).count() <= 1


def can_grant_permission(actor, permission):
    """Un actor solo puede conceder permisos que ya posee.

    El superadministrador puede conceder cualquiera. Los permisos
    reservados nunca se conceden a roles personalizados.
    """
    if is_system_admin(actor):
        return True
    if permission.is_reserved:
        return False
    return has_permission(actor, permission.code)
