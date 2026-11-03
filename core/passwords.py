"""Política única de contraseñas para todos los flujos de GO VISTA.

No depende del usuario de Django: el proyecto usa ``core.User``. Todos los
altas, cambios y restablecimientos deben pasar por ``validate_password``.
"""

from django.conf import settings

from .models import normalize_user_name


class PasswordPolicyError(ValueError):
    pass


COMMON_PASSWORDS = {
    '123456', '12345678', '123456789', '1234567890', 'password',
    'password1', 'qwerty', 'qwerty123', 'admin', 'admin123', 'administrador',
    'ventas', 'caja', 'callcenter', 'govista', 'salestracker', 'iloveyou',
    'bienvenido', 'contraseña', 'contrasena',
}


def _min_length():
    return int(getattr(settings, 'PASSWORD_MIN_LENGTH', 10))


def validate_password(raw, user=None):
    """Valida y devuelve la contraseña; lanza PasswordPolicyError."""
    if raw is None:
        raise PasswordPolicyError('La contraseña es obligatoria.')
    if not isinstance(raw, str):
        raise PasswordPolicyError('La contraseña no es válida.')
    if len(raw) < _min_length():
        raise PasswordPolicyError(
            f'La contraseña debe tener al menos {_min_length()} caracteres.')
    if len(raw) > 128:
        raise PasswordPolicyError(
            'La contraseña no puede superar los 128 caracteres.')
    if raw.strip() != raw:
        raise PasswordPolicyError(
            'La contraseña no puede empezar ni terminar con espacios.')
    if raw.casefold() in COMMON_PASSWORDS:
        raise PasswordPolicyError('Esa contraseña es demasiado común.')
    if raw.isdigit():
        raise PasswordPolicyError(
            'La contraseña no puede contener solo números.')

    if user is not None:
        name = normalize_user_name(getattr(user, 'name', ''))
        candidate = raw.casefold()
        if name and (candidate == name or name in candidate):
            raise PasswordPolicyError(
                'La contraseña no puede contener el nombre de usuario.')

    return raw


def validate_password_confirmation(password, confirmation):
    if password != confirmation:
        raise PasswordPolicyError('Las contraseñas no coinciden.')
    return password
