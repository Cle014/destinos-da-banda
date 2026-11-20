# =============================================================
# config/settings/__init__.py
# =============================================================
# Este ficheiro carrega automaticamente o settings correcto
# dependendo da variável de ambiente ENVIRONMENT.
#
# Porquê separar os settings?
# - Em desenvolvimento queremos debug ativo, logs verbosos, etc.
# - Em produção queremos segurança máxima, sem debug, com cache.
# - Misturar os dois num único ficheiro é uma má prática.
# =============================================================

import os
from decouple import config

# Ler o ambiente actual — padrão é "development" se não definido
environment = config('ENVIRONMENT', default='development')

if environment == 'production':
    from .production import *
else:
    from .development import *
