# =============================================================
# apps/core/apps.py — Configuração da App Core
# =============================================================

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Caminho completo necessário porque a app está dentro de 'apps/'
    name = 'apps.core'
    verbose_name = 'Core'
