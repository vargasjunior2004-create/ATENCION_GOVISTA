"""
Django settings for salestracker project.

Generado por 'django-admin startproject' usando Django 6.0.
Backend de la planilla de ventas diarias (SaleStracker).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-mock-key-salestracker-cambiar-en-produccion')

DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() in ('1', 'true', 'yes')

_env_hosts = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
ALLOWED_HOSTS = list(set(_env_hosts + ['localhost', '127.0.0.1', '.onrender.com', '.wasmer.app']))

_env_origins = [o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
CSRF_TRUSTED_ORIGINS = list(set(_env_origins + ['https://*.onrender.com', 'https://*.wasmer.app']))

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
}

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ACCESS_TOKEN_LIFETIME': __import__('datetime').timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': __import__('datetime').timedelta(hours=1),
    'ROTATE_REFRESH_TOKENS': False,
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

# Ruta donde se sirve el build del frontend React (producción)
FRONTEND_BUILD_DIR = BASE_DIR / 'frontend_build'
