"""
Django settings for salestracker project.

Generado por 'django-admin startproject' usando Django 6.0.
Backend de la planilla de ventas diarias (SaleStracker).
"""

import os
import dj_database_url
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_environment = os.environ.get('DJANGO_ENV', 'development').lower()
_debug_value = os.environ.get('DJANGO_DEBUG')
if _environment in ('prod', 'production') and _debug_value is None:
    raise ImproperlyConfigured('DJANGO_DEBUG debe definirse explícitamente en producción.')
DEBUG = (_debug_value or 'true').lower() in ('1', 'true', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError(
            'DJANGO_SECRET_KEY es obligatoria cuando DJANGO_DEBUG=false.')
    SECRET_KEY = 'local-development-only-key-not-for-production'

_env_hosts = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
if DEBUG:
    ALLOWED_HOSTS = list(set(_env_hosts + ['localhost', '127.0.0.1']))
elif not _env_hosts:
    raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS es obligatoria en producción.')
else:
    ALLOWED_HOSTS = _env_hosts

_env_origins = [o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
if DEBUG:
    CSRF_TRUSTED_ORIGINS = _env_origins
elif not _env_origins:
    raise ImproperlyConfigured('DJANGO_CSRF_TRUSTED_ORIGINS es obligatoria en producción.')
else:
    CSRF_TRUSTED_ORIGINS = _env_origins

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'salestracker.error_middleware.RequestIDMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'salestracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'frontend_build'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'salestracker.wsgi.application'

# La credencial de la base de datos SOLO se lee de variables de entorno.
# Nunca se escribe una credencial real en el repositorio.
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DEBUG and not DATABASE_URL:
    raise ImproperlyConfigured('DATABASE_URL es obligatoria en producción.')
if not DEBUG and DATABASE_URL and DATABASE_URL.startswith('sqlite'):
    raise ImproperlyConfigured('SQLite no está permitido en producción.')
if DATABASE_URL:
    # El SSL es obligatorio por defecto (Supabase lo exige). Solo se relaja
    # si se define DB_SSL_DISABLE=1, usado exclusivamente para levantar un
    # PostgreSQL local de pruebas que no tiene certificado.
    _db_ssl_disable = os.environ.get('DB_SSL_DISABLE', '').lower() in (
        '1', 'true', 'yes')

    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=not _db_ssl_disable,
        )
    }
else:
    _db_path = os.environ.get('SQLITE_PATH', str(BASE_DIR / 'data' / 'db.sqlite3'))
    try:
        os.makedirs(os.path.dirname(_db_path), exist_ok=True)
        _test = os.path.join(os.path.dirname(_db_path), '.write_test')
        open(_test, 'w').close()
        os.remove(_test)
    except OSError:
        _db_path = str(BASE_DIR / 'db.sqlite3')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': _db_path,
            'OPTIONS': {
                'init_command': 'PRAGMA journal_mode=WAL; PRAGMA busy_timeout=30000; PRAGMA foreign_keys=ON;',
            },
        }
    }

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/La_Paz'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

STATICFILES_DIRS = [BASE_DIR / 'frontend_build' / 'static']

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.auth.CoreJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_RATES': {
        'report_link': '10/hour',
        'report_public': '30/hour',
    },
}

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ACCESS_TOKEN_LIFETIME': __import__('datetime').timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': __import__('datetime').timedelta(hours=8),
    'ROTATE_REFRESH_TOKENS': True,
    # token_blacklist requiere AUTH_USER_MODEL de Django; este proyecto usa
    # core.User y la integración se planifica para una fase de autenticación.
    'BLACKLIST_AFTER_ROTATION': False,
}

SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_HSTS_SECONDS = 3600 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

# Ruta donde se sirve el build del frontend React (producción)
FRONTEND_BUILD_DIR = BASE_DIR / 'frontend_build'
