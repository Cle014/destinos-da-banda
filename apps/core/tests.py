import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accommodations.models import Accommodation, Booking
from apps.dashboard.forms import CategoryForm, DestinationQuickForm
from apps.destinations.models import Category, Destination, destination_image_path
from apps.guides.models import AvaliacaoGuia, GuiaTuristico, guide_photo_path
from apps.routes.models import Route, RouteStop


class RoutesMapXSSTests(TestCase):
    """VULN-01: Testa prevenção de Stored XSS no mapa Leaflet de rotas."""

    def setUp(self):
        self.cat = Category.objects.create(name='Natureza', color='#006B3C', icon='fas fa-tree')
        self.xss_dest = Destination.objects.create(
            name='</script><script>window.__xss=1;</script><img src=x onerror=alert(1)>',
            category=self.cat,
            province='malanje',
            short_description='Resumo seguro',
            description='Descrição segura',
            latitude=-9.073800,
            longitude=16.000500,
            image_url='https://example.com/img.jpg',
            status='published',
        )
        self.route = Route.objects.create(
            name='Rota Teste Segurança',
            short_description='Resumo da rota',
            description='Descrição completa da rota',
            duration_days=2,
            difficulty='easy',
            status='published',
        )
        RouteStop.objects.create(
            route=self.route,
            destination=self.xss_dest,
            day=1,
            order=1,
        )

    def test_route_detail_escapes_script_breakout_in_map_points(self):
        response = self.client.get(reverse('routes:detail', kwargs={'slug': self.route.slug}))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        # O payload bruto nunca pode surgir não escapado dentro de um bloco <script>
        self.assertNotIn('</script><script>window.__xss=1;</script>', html)
        # Deve usar json_script com escape Unicode (\u003C)
        self.assertIn('id="route-map-points"', html)
        self.assertIn('\\u003C/script\\u003E', html)


class SecretsAndHeadersSecurityTests(TestCase):
    """VULN-02 e VULN-09: Testa segredos, .gitignore e cabeçalhos HTTP de segurança."""

    def test_secret_key_is_strong_and_not_placeholder(self):
        self.assertFalse(settings.SECRET_KEY.startswith('django-insecure-'))
        self.assertNotEqual(settings.SECRET_KEY, 'gerar-uma-chave-unica-aqui')
        self.assertGreaterEqual(len(settings.SECRET_KEY), 50)

    def test_gitignore_protects_env_and_sqlite(self):
        gitignore_path = Path(settings.BASE_DIR) / '.gitignore'
        self.assertTrue(gitignore_path.exists(), '.gitignore deve existir na raiz do projeto')
        content = gitignore_path.read_text(encoding='utf-8')
        self.assertIn('.env', content)
        self.assertIn('db.sqlite3', content)

    def test_http_security_headers_present_on_public_pages(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.headers.get('Referrer-Policy'), 'same-origin')
        self.assertEqual(response.headers.get('Cross-Origin-Opener-Policy'), 'same-origin')
        self.assertIn('geolocation=()', response.headers.get('Permissions-Policy', ''))
        self.assertIn("frame-ancestors 'none'", response.headers.get('Content-Security-Policy', ''))


class AdminAndDashboardAccessControlTests(TestCase):
    """VULN-03: Testa controlo de acesso, CSRF, Open Redirect e força bruta no Painel e Admin."""

    def setUp(self):
        cache.clear()
        self.staff_user = User.objects.create_user(
            username='admin_sec',
            email='admin@destinosdabanda.ao',
            password='StrongPassword!2026',
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            username='turista',
            email='turista@destinosdabanda.ao',
            password='TuristaPassword!2026',
            is_staff=False,
        )

    def tearDown(self):
        cache.clear()

    def test_anonymous_and_non_staff_cannot_access_dashboard(self):
        res_anon = self.client.get(reverse('dashboard:home'))
        self.assertEqual(res_anon.status_code, 302)
        self.assertIn(reverse('dashboard:login'), res_anon['Location'])

        self.client.force_login(self.normal_user)
        res_user = self.client.get(reverse('dashboard:home'))
        self.assertEqual(res_user.status_code, 302)
        self.assertIn(reverse('dashboard:login'), res_user['Location'])

        # Utilizador não-staff não pode criar categorias
        res_post = self.client.post(reverse('dashboard:category_add'), {
            'name': 'Invasão',
            'icon': 'fas fa-bug',
            'color': '#123456',
            'order': 1,
        })
        self.assertEqual(res_post.status_code, 302)
        self.assertFalse(Category.objects.filter(name='Invasão').exists())

    def test_logout_requires_post(self):
        self.client.force_login(self.staff_user)
        res_get = self.client.get(reverse('dashboard:logout'))
        self.assertEqual(res_get.status_code, 405)

    def test_login_blocks_open_redirect(self):
        res = self.client.post(reverse('dashboard:login'), {
            'username': 'admin_sec',
            'password': 'StrongPassword!2026',
            'next': 'https://unknown-external.example.org/redirect',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res['Location'], reverse('dashboard:home'))

    @override_settings(DASHBOARD_LOGIN_MAX_ATTEMPTS=3, DASHBOARD_LOGIN_LOCKOUT_SECONDS=300)
    def test_brute_force_lockout_on_dashboard_and_django_admin(self):
        login_url = reverse('dashboard:login')
        for _ in range(3):
            r = self.client.post(login_url, {'username': 'admin_sec', 'password': 'wrong'})
            self.assertEqual(r.status_code, 200)

        # 4ª tentativa é bloqueada com HTTP 429 no painel
        r_locked = self.client.post(login_url, {'username': 'admin_sec', 'password': 'StrongPassword!2026'})
        self.assertEqual(r_locked.status_code, 429)

        # O mesmo bloqueio protege o login do Django Admin
        admin_login_url = reverse('admin:login')
        r_admin_locked = self.client.post(admin_login_url, {'username': 'admin_sec', 'password': 'StrongPassword!2026'})
        self.assertEqual(r_admin_locked.status_code, 429)

    @override_settings(DASHBOARD_LOGIN_MAX_ATTEMPTS=3, DASHBOARD_LOGIN_LOCKOUT_SECONDS=300)
    def test_django_admin_login_registers_failed_attempts(self):
        admin_login_url = reverse('admin:login')
        for _ in range(3):
            self.client.post(admin_login_url, {'username': 'admin_sec', 'password': 'wrong'})

        r_locked = self.client.post(admin_login_url, {'username': 'admin_sec', 'password': 'StrongPassword!2026'})
        self.assertEqual(r_locked.status_code, 429)

    def test_guide_detail_does_not_expose_admin_login_url(self):
        guide = GuiaTuristico.objects.create(
            nome='Guia Teste',
            biografia='Bio',
            provincia='luanda',
            activo=True,
        )
        res = self.client.get(reverse('guides:detail', kwargs={'slug': guide.slug}))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode('utf-8')
        self.assertNotIn(reverse('admin:login'), html)
        self.assertIn(reverse('dashboard:login'), html)


class GuideReviewValidationTests(TestCase):
    """VULN-04: Testa validação de intervalos nas avaliações de guias."""

    def setUp(self):
        self.user = User.objects.create_user(username='avaliador', password='Password!123')
        self.guide = GuiaTuristico.objects.create(
            nome='Mateus Kiala',
            biografia='Guia experiente',
            provincia='huila',
            activo=True,
        )

    def test_rejects_out_of_range_and_non_integer_ratings(self):
        self.client.force_login(self.user)
        url = reverse('guides:avaliar', kwargs={'slug': self.guide.slug})

        # GET não permitido
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, 405)

        # Classificação acima do limite (999)
        self.client.post(url, {
            'classificacao': 999,
            'pontualidade': 5,
            'simpatia': 5,
            'conhecimento': 5,
            'organizacao': 5,
        })
        self.assertEqual(AvaliacaoGuia.objects.count(), 0)

        # Classificação abaixo do limite (0)
        self.client.post(url, {
            'classificacao': 0,
            'pontualidade': 5,
            'simpatia': 5,
            'conhecimento': 5,
            'organizacao': 5,
        })
        self.assertEqual(AvaliacaoGuia.objects.count(), 0)

        # Classificação inválida não numérica
        self.client.post(url, {
            'classificacao': 'cinco',
            'pontualidade': 5,
            'simpatia': 5,
            'conhecimento': 5,
            'organizacao': 5,
        })
        self.assertEqual(AvaliacaoGuia.objects.count(), 0)

        # Classificação válida (4)
        self.client.post(url, {
            'classificacao': 4,
            'pontualidade': 5,
            'simpatia': 4,
            'conhecimento': 5,
            'organizacao': 4,
            'comentario': 'Excelente passeio!',
        })
        self.assertEqual(AvaliacaoGuia.objects.count(), 1)
        self.guide.refresh_from_db()
        self.assertEqual(float(self.guide.avaliacao_media), 4.0)


class AccommodationBookingSecurityTests(TestCase):
    """VULN-05: Testa validação de inputs, alojamentos inativos e rate-limiting em reservas."""

    def setUp(self):
        cache.clear()
        self.active_acc = Accommodation.objects.create(
            name='Lodge Ativo',
            accommodation_type='lodge',
            province='huila',
            city='Lubango',
            short_description='Curta',
            description='Completa',
            price_per_night_aoa=50000,
            max_guests=3,
            is_active=True,
        )
        self.inactive_acc = Accommodation.objects.create(
            name='Hotel Inativo',
            accommodation_type='hotel',
            province='luanda',
            city='Luanda',
            short_description='Curta',
            description='Completa',
            price_per_night_aoa=80000,
            max_guests=2,
            is_active=False,
        )
        self.tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.day_after = (datetime.date.today() + datetime.timedelta(days=3)).strftime('%Y-%m-%d')

    def tearDown(self):
        cache.clear()

    def test_invalid_guests_count_does_not_crash_with_500(self):
        url = reverse('accommodations:book', kwargs={'slug': self.active_acc.slug})
        res = self.client.post(url, {
            'guest_name': 'João Silva',
            'guest_email': 'joao@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': self.tomorrow,
            'check_out': self.day_after,
            'guests_count': 'invalido_nao_numerico',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Booking.objects.count(), 0)

    def test_rejects_excessive_or_negative_guests_and_invalid_dates(self):
        url = reverse('accommodations:book', kwargs={'slug': self.active_acc.slug})

        # Hóspedes acima da capacidade máxima (max_guests=3)
        self.client.post(url, {
            'guest_name': 'João Silva',
            'guest_email': 'joao@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': self.tomorrow,
            'check_out': self.day_after,
            'guests_count': 10,
        })
        self.assertEqual(Booking.objects.count(), 0)

        # Hóspedes negativos
        self.client.post(url, {
            'guest_name': 'João Silva',
            'guest_email': 'joao@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': self.tomorrow,
            'check_out': self.day_after,
            'guests_count': -1,
        })
        self.assertEqual(Booking.objects.count(), 0)

        # Estadia superior a 365 dias
        far_future = (datetime.date.today() + datetime.timedelta(days=500)).strftime('%Y-%m-%d')
        self.client.post(url, {
            'guest_name': 'João Silva',
            'guest_email': 'joao@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': self.tomorrow,
            'check_out': far_future,
            'guests_count': 2,
        })
        self.assertEqual(Booking.objects.count(), 0)

    def test_cannot_book_inactive_accommodation(self):
        url = reverse('accommodations:book', kwargs={'slug': self.inactive_acc.slug})
        res = self.client.post(url, {
            'guest_name': 'João Silva',
            'guest_email': 'joao@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': self.tomorrow,
            'check_out': self.day_after,
            'guests_count': 2,
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Booking.objects.count(), 0)

    @override_settings(BOOKING_MAX_PER_IP=2, BOOKING_RATE_LIMIT_SECONDS=600)
    def test_booking_rate_limit_blocks_flooding(self):
        url = reverse('accommodations:book', kwargs={'slug': self.active_acc.slug})
        payload = {
            'guest_name': 'Maria Costa',
            'guest_email': 'maria@example.com',
            'guest_phone': '+244 923 000 111',
            'check_in': self.tomorrow,
            'check_out': self.day_after,
            'guests_count': 2,
        }
        r1 = self.client.post(url, payload)
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.post(url, payload)
        self.assertEqual(r2.status_code, 200)

        # 3º pedido seguido do mesmo IP é bloqueado com HTTP 429
        r3 = self.client.post(url, payload)
        self.assertEqual(r3.status_code, 429)
        self.assertEqual(Booking.objects.count(), 2)


class FormsUploadAndCSSInjectionTests(TestCase):
    """VULN-07 e VULN-08: Testa prevenção de CSS/URL injection e uploads maliciosos."""

    def test_category_form_rejects_css_and_icon_injection(self):
        form_bad_color = CategoryForm(data={
            'name': 'Teste Cor',
            'icon': 'fas fa-sun',
            'color': '#000;background:url(x)',
            'order': 1,
        })
        self.assertFalse(form_bad_color.is_valid())
        self.assertIn('color', form_bad_color.errors)

        form_bad_icon = CategoryForm(data={
            'name': 'Teste Icon',
            'icon': 'fas fa-sun" onclick="alert(1)',
            'color': '#006B3C',
            'order': 1,
        })
        self.assertFalse(form_bad_icon.is_valid())
        self.assertIn('icon', form_bad_icon.errors)

    def test_destination_form_rejects_unsafe_image_url_and_bad_uploads(self):
        form_bad_url = DestinationQuickForm(data={
            'name': 'Destino URL Malicioso',
            'province': 'luanda',
            'short_description': 'Curta',
            'description': 'Descrição',
            'image_url': "https://example.com/foto.jpg');alert(1);//",
            'status': 'draft',
        })
        self.assertFalse(form_bad_url.is_valid())
        self.assertIn('image_url', form_bad_url.errors)

        # Upload com extensão não permitida (.txt / .exe)
        bad_file = SimpleUploadedFile('invalid_file.txt', b'plain text content not an image', content_type='text/plain')
        form_bad_ext = DestinationQuickForm(
            data={
                'name': 'Destino Upload Invalido',
                'province': 'luanda',
                'short_description': 'Curta',
                'description': 'Descrição',
                'status': 'draft',
            },
            files={'image': bad_file},
        )
        self.assertFalse(form_bad_ext.is_valid())
        self.assertIn('image', form_bad_ext.errors)

    def test_upload_path_functions_sanitize_extensions(self):
        dest = Destination(name='Quedas de Kalandula', slug='quedas-kalandula')
        path = destination_image_path(dest, '../../untrusted.ext')
        self.assertTrue(path.endswith('.jpg'))
        self.assertNotIn('..', path)

        guide = GuiaTuristico(nome='Guia', slug='guia-teste')
        g_path = guide_photo_path(guide, 'payload.svg')
        self.assertEqual(g_path, 'guides/guia-teste.jpg')
