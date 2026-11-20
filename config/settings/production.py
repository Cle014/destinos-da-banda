# =============================================================
# config/settings/production.py — AMBIENTE DE PRODUÇÃO
# =============================================================
# Configurações de segurança máxima para o servidor em produção.
# Todos os valores sensíveis vêm do .env.
# =============================================================

import os
from .base import *
from decouple import config
from django.core.exceptions import ImproperlyConfigured

# CRÍTICO: Debug DESLIGADO em produção
# Com Debug=True em produção: exposição de código, paths, variáveis
DEBUG = False

if (
    not SECRET_KEY
    or SECRET_KEY.startswith('django-insecure-')
    or SECRET_KEY == 'gerar-uma-chave-unica-aqui'
    or len(SECRET_KEY) < 32
):
    raise ImproperlyConfigured(
        'Em produção, SECRET_KEY deve ter pelo menos 32 caracteres e não pode usar um valor de exemplo ou django-insecure-.'
    )

# Apenas os domínios reais do projecto (+ hostname automático do Render.com)
ALLOWED_HOSTS = [h.strip() for h in config('ALLOWED_HOSTS', default='').split(',') if h.strip()]
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if o.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

# Base de dados: usa DATABASE_URL (PostgreSQL no Render) ou SQLite como fallback
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(_database_url, conn_max_age=600, ssl_require=True)
    }

# WhiteNoise em produção: não falhar se algum CSS referenciar asset externo/opcional
WHITENOISE_MANIFEST_STRICT = False

# =============================================================
# SEGURANÇA HTTP — headers de segurança obrigatórios
# =============================================================

# Forçar HTTPS — redireciona HTTP para HTTPS automaticamente
SECURE_SSL_REDIRECT = True

# Cookie de sessão só via HTTPS
SESSION_COOKIE_SECURE = True

# Cookie CSRF só via HTTPS
CSRF_COOKIE_SECURE = True

# HSTS: dizer ao browser para usar sempre HTTPS (1 ano)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Prevenir MIME-type sniffing pelo browser
SECURE_CONTENT_TYPE_NOSNIFF = True

# Protecção XSS no browser (header legado mas ainda útil)
SECURE_BROWSER_XSS_FILTER = True

# Não permitir o site em iframes (protecção clickjacking)
X_FRAME_OPTIONS = 'DENY'

# Não enviar o URL completo como Referer para outros sites
SECURE_REFERRER_POLICY = 'same-origin'

# O Django atrás de proxy HTTPS (Render, Railway, nginx) precisa deste header
# para reconhecer pedidos HTTPS e evitar loops de redireccionamento:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Em produção, exigir caminhos próprios para o admin e o painel (não usar os padrão).
if ADMIN_URL in ('admin/', 'django-admin/') or DASHBOARD_URL == 'painel/':
    import warnings
    warnings.warn(
        'Defina ADMIN_URL e DASHBOARD_URL no .env com caminhos difíceis de adivinhar.',
        RuntimeWarning,
    )

# =============================================================
# CACHE em produção (a configurar com Redis futuramente)
# =============================================================
# Por agora usa cache em memória — na fase 8 migrar para Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# =============================================================
# LOGS em produção: guardar em ficheiros
# =============================================================
(BASE_DIR / 'logs').mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'production': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/production.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'production',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/errors.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'level': 'ERROR',
            'formatter': 'production',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
        },
        'apps': {
            'handlers': ['file', 'error_file'],
            'level': 'WARNING',
        },
    },
}
