#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements/prod.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

if [ -f "initial_data.json" ]; then
  python manage.py shell -c "
from apps.destinations.models import Destination
from django.core.management import call_command
if Destination.objects.count() == 0:
    call_command('loaddata', 'initial_data.json')
    print('Dados iniciais carregados com sucesso.')
"
fi

if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
u = os.environ['DJANGO_SUPERUSER_USERNAME']
p = os.environ['DJANGO_SUPERUSER_PASSWORD']
e = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@destinosdabanda.ao')
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(username=u, email=e, password=p)
    print(f'Superuser {u} criado.')
"
fi
