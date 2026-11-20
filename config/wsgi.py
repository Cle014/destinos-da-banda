# =============================================================
# config/wsgi.py — Interface WSGI para produção
# Usado por: Gunicorn, uWSGI, Apache mod_wsgi
# =============================================================

import os
from django.core.wsgi import get_wsgi_application

# O settings/__init__.py escolhe o ambiente correcto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
