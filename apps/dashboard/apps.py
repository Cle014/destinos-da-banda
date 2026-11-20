from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.dashboard'
    verbose_name = 'Painel de Gestão'

    def ready(self):
        from urllib.parse import urlencode
        from django.contrib import admin
        from django.shortcuts import redirect
        from django.urls import reverse

        def protected_admin_login(request, extra_context=None):
            next_url = request.GET.get('next') or reverse('dashboard:home')
            return redirect(f"{reverse('dashboard:login')}?{urlencode({'next': next_url})}")

        admin.site.login = protected_admin_login
