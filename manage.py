#!/usr/bin/env python
"""
manage.py — Utilitário de gestão do Django
Ponto de entrada para comandos como: runserver, migrate, makemigrations, etc.
"""
import os
import sys


def main():
    """Executa comandos administrativos do Django."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. "
            "Verifica se o Django está instalado e o ambiente virtual activado."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
