import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',        # Django REST Framework — API
    'django_filters',        # Filtros para querysets (fase 3)

    'apps.core',
    'apps.destinations',
    'apps.gallery',
    'apps.accommodations',
    'apps.events',
    'apps.routes',
    'apps.guides',
    'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.dashboard.middleware.DashboardSecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

_db_engine = config('DB_ENGINE', default='django.db.backends.sqlite3')
_db_name   = config('DB_NAME',   default='db.sqlite3')

_db_config = {
    'ENGINE': _db_engine,
    'NAME':   BASE_DIR / _db_name if 'sqlite3' in _db_engine else _db_name,
}

if 'sqlite3' not in _db_engine:
    _db_config.update({
        'USER':     config('DB_USER',     default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST':     config('DB_HOST',     default='localhost'),
        'PORT':     config('DB_PORT',     default='5432'),
        'OPTIONS':  {'connect_timeout': 10} if 'postgresql' in _db_engine else {},
    })

DATABASES = {'default': _db_config}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-ao'  # Português de Angola
TIME_ZONE = 'Africa/Luanda'
USE_I18N = True
USE_TZ = True  # Sempre usar timezone-aware datetimes

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 12,  # 12 resultados por página (bom para grids)

    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],

    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    }
}

# =============================================================
# ACESSO AO PAINEL E AO ADMIN
# =============================================================
# Caminhos configuráveis por .env. Em produção use valores difíceis de adivinhar,
# ex: ADMIN_URL=gestao-7f3k9q/django/  DASHBOARD_URL=gestao-7f3k9q/
ADMIN_URL = config('ADMIN_URL', default='django-admin/')
DASHBOARD_URL = config('DASHBOARD_URL', default='painel/')
for _name, _value in (('ADMIN_URL', ADMIN_URL), ('DASHBOARD_URL', DASHBOARD_URL)):
    if not _value.endswith('/') or _value.startswith('/'):
        raise ValueError(f"{_name} deve terminar em '/' e não começar por '/' (ex: 'painel/').")

LOGIN_URL = 'dashboard:login'
LOGIN_REDIRECT_URL = 'dashboard:home'

# Protecção contra força bruta no login
DASHBOARD_LOGIN_MAX_ATTEMPTS = config('DASHBOARD_LOGIN_MAX_ATTEMPTS', default=5, cast=int)          # por IP + utilizador
DASHBOARD_LOGIN_MAX_ATTEMPTS_PER_IP = config('DASHBOARD_LOGIN_MAX_ATTEMPTS_PER_IP', default=20, cast=int)
DASHBOARD_LOGIN_LOCKOUT_SECONDS = config('DASHBOARD_LOGIN_LOCKOUT_SECONDS', default=900, cast=int)   # 15 min

# Rate-limiting no pedido de reservas públicas
BOOKING_MAX_PER_IP = config('BOOKING_MAX_PER_IP', default=5, cast=int)
BOOKING_RATE_LIMIT_SECONDS = config('BOOKING_RATE_LIMIT_SECONDS', default=900, cast=int)

# Sessões de staff terminam após inactividade (segundos)
STAFF_SESSION_IDLE_TIMEOUT = config('STAFF_SESSION_IDLE_TIMEOUT', default=1800, cast=int)          # 30 min

# Cookies & Headers de Segurança Base
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Uploads
MAX_UPLOAD_IMAGE_MB = config('MAX_UPLOAD_IMAGE_MB', default=8, cast=int)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

# =============================================================
# ESTRATÉGIA DE CUNHA E DENSIDADE DO ECOSSISTEMA
# =============================================================
# Província activa padrão da cunha e limiar mínimo de itens activos por módulo
DEFAULT_ACTIVE_PROVINCE = config('DEFAULT_ACTIVE_PROVINCE', default='huambo')
MIN_MODULE_ITEMS_PER_PROVINCE = config('MIN_MODULE_ITEMS_PER_PROVINCE', default=5, cast=int)
STALE_RECORD_DAYS = config('STALE_RECORD_DAYS', default=60, cast=int)
LONG_DISTANCE_THRESHOLD_KM = config('LONG_DISTANCE_THRESHOLD_KM', default=55, cast=int)
AVERAGE_ROAD_SPEED_KMH = config('AVERAGE_ROAD_SPEED_KMH', default=50, cast=int)
