"""Registro de intentos de inicio de sesión compartido entre workers."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LoginAttempt


def client_ip(request):
    """IP real del cliente.

    En Render la petición llega desde un proxy. Solo se confía en
    X-Forwarded-For cuando la configuración lo autoriza explícitamente.
    """
    if getattr(settings, 'TRUST_PROXY_HEADERS', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _window_start():
    minutes = int(getattr(settings, 'LOGIN_WINDOW_MINUTES', 15))
    return timezone.now() - timedelta(minutes=minutes)


def lockout_remaining(username, ip=None):
    """No aplica bloqueo automático; se conserva por compatibilidad de API."""
    return 0


def record_attempt(username, ip, successful, user_agent=''):
    return LoginAttempt.objects.create(
        username=username,
        ip=ip,
        successful=successful,
        user_agent=(user_agent or '')[:255],
    )


def register_failure(user, username, ip, user_agent=''):
    record_attempt(username, ip, False, user_agent)
    if user is None:
        return
    window_failures = LoginAttempt.objects.filter(
        created_at__gte=_window_start(),
        successful=False,
    ).filter(username=username).count()
    user.failed_login_count = window_failures
    # Los intentos fallidos se conservan para auditoría, pero no bloquean
    # automáticamente al usuario.
    user.locked_until = None
    user.save(update_fields=['failed_login_count', 'locked_until'])


def register_success(user, username, ip, user_agent=''):
    record_attempt(username, ip, True, user_agent)
    user.last_login_at = timezone.now()
    user.last_login_ip = ip
    user.failed_login_count = 0
    user.locked_until = None
    user.save(update_fields=[
        'last_login_at', 'last_login_ip',
        'failed_login_count', 'locked_until',
    ])


def unlock_user(user):
    user.failed_login_count = 0
    user.locked_until = None
    user.save(update_fields=['failed_login_count', 'locked_until'])
