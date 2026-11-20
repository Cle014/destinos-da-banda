# =============================================================
# config/settings/development.py — AMBIENTE DE DESENVOLVIMENTO
# =============================================================
# Configurações específicas para desenvolvimento local.
# NUNCA usar estas configurações em produção.
# =============================================================

import sys
from .base import *
from decouple import config

TESTING = 'test' in sys.argv

# Em desenvolvimento: debug activo para ver erros detalhados
DEBUG = config('DEBUG', default=True, cast=bool)

# Em desenvolvimento: aceitar hosts locais e túneis de demonstração (Cloudflare / localhost.run)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',') + [
    '.trycloudflare.com',
    '.lhr.life',
    '.onrender.com',
]
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://*.trycloudflare.com',
    'https://*.lhr.life',
    'https://*.onrender.com',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# =============================================================
# DESENVOLVIMENTO: adicionar debug toolbar e extensões
# =============================================================
INSTALLED_APPS += [
    'django_extensions',  # Comandos extra de management
]

if not TESTING:
    INSTALLED_APPS += [
        'debug_toolbar',  # Barra de depuração visual
    ]
    MIDDLEWARE = [
        # Debug toolbar deve ser o primeiro middleware
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ] + MIDDLEWARE

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Debug toolbar só activa para IPs locais
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# =============================================================
# DRF em desenvolvimento: adicionar interface visual da API
# =============================================================
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',  # Interface HTML da API
]

# =============================================================
# LOGS em desenvolvimento: mostrar queries SQL na consola
# =============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        # Mostrar queries SQL (útil para optimização)
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Logger da nossa aplicação
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =============================================================
# EMAIL em desenvolvimento: mostrar emails na consola
# (em vez de enviar emails reais)
# =============================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
