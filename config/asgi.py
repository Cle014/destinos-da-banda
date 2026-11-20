# =============================================================
# config/asgi.py — Interface ASGI para suporte a WebSockets
# Preparado para futuras funcionalidades em tempo real
# (ex: chat com guia, notificações, mapas ao vivo)
# =============================================================

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
