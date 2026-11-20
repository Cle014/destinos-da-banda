"""Middleware de segurança do Painel de Gestão, Django Admin e Headers HTTP.

- Sessões de staff expiram após inactividade (STAFF_SESSION_IDLE_TIMEOUT).
- Protecção contra força bruta também aplicada ao endpoint de login do Django Admin.
- Páginas do painel/admin nunca ficam em cache do navegador ou de proxies.
- Páginas do painel/admin não são indexadas por motores de pesquisa.
- Cabeçalhos defensivos Content-Security-Policy e Permissions-Policy.
"""
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils.cache import add_never_cache_headers

from .views import _client_ip, _clear_failures, _is_locked, _register_failure, security_log


class DashboardSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._prefixes = None
        self._admin_login_path = None

    def _protected_prefixes(self):
        if self._prefixes is None:
            self._prefixes = (reverse('dashboard:home'), reverse('admin:index'))
        return self._prefixes

    def _get_admin_login_path(self):
        if self._admin_login_path is None:
            self._admin_login_path = reverse('admin:login')
        return self._admin_login_path

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and (user.is_staff or user.is_superuser):
            # Expiração deslizante: cada pedido renova o prazo; inactividade termina a sessão.
            request.session.set_expiry(settings.STAFF_SESSION_IDLE_TIMEOUT)

        admin_login_path = self._get_admin_login_path()
        is_admin_login_post = request.method == 'POST' and request.path == admin_login_path

        if is_admin_login_post:
            ip = _client_ip(request)
            username = request.POST.get('username', '').strip()[:150]
            if _is_locked(ip, username):
                security_log.warning('Login bloqueado no Django Admin ip=%s user=%s', ip, username)
                minutes = settings.DASHBOARD_LOGIN_LOCKOUT_SECONDS // 60
                response = HttpResponse(
                    f"Demasiadas tentativas falhadas. Tente novamente dentro de {minutes} minutos.",
                    status=429,
                    content_type='text/plain; charset=utf-8',
                )
                add_never_cache_headers(response)
                response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
                return response

        response = self.get_response(request)

        if is_admin_login_post:
            ip = _client_ip(request)
            username = request.POST.get('username', '').strip()[:150]
            post_user = getattr(request, 'user', None)
            if post_user is not None and post_user.is_authenticated and (post_user.is_staff or post_user.is_superuser):
                _clear_failures(ip, username)
            else:
                _register_failure(ip, username)
                security_log.warning('Login falhado no Django Admin ip=%s user=%s', ip, username)

        if request.path.startswith(self._protected_prefixes()):
            add_never_cache_headers(response)
            response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'

        if 'Permissions-Policy' not in response:
            response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), payment=()'
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"

        return response
