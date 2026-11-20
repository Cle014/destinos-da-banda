import datetime

from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accommodations.models import Accommodation, Booking, RoomType, TripOrder
from apps.dashboard import views as dashboard_views
from apps.dashboard.forms import (
    BookingForm,
    EspecialidadeForm,
    EventQuickForm,
    TripOrderForm,
)
from apps.destinations.models import Category, CulturalArticle, Destination, DestinationVisitBooking
from apps.events.models import Event, EventBooking
from apps.gallery.models import GalleryItem
from apps.guides.models import Especialidade, GuiaTuristico
from apps.routes.models import Route, RouteStop


class DashboardCRUDTests(TestCase):
    """Testes completos de CRUD (Criar, Ler, Actualizar, Eliminar) no Painel Administrativo."""

    def setUp(self):
        self.factory = RequestFactory()
        self.staff = User.objects.create_user(
            username='gestor_crud',
            email='gestor@destinosdabanda.ao',
            password='StrongPassword!2026',
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            username='visitante_crud',
            email='visitante@destinosdabanda.ao',
            password='UserPassword!2026',
            is_staff=False,
        )
        self.client.force_login(self.staff)

        self.category = Category.objects.create(
            name='Natureza', icon='fas fa-leaf', color='#006B3C', order=1
        )
        self.destination = Destination.objects.create(
            name='Quedas de Kalandula',
            category=self.category,
            province='malanje',
            short_description='Resumo',
            description='Descrição completa',
            entry_fee_min_aoa=5000,
            status='published',
        )
        self.accommodation = Accommodation.objects.create(
            name='Lodge do Planalto',
            accommodation_type='lodge',
            province='huambo',
            city='Huambo',
            short_description='Lodge confortável',
            description='Descrição do lodge',
            price_per_night_aoa=45000,
            is_active=True,
        )
        self.event = Event.objects.create(
            title='Tour Serra da Leba',
            activity_type='tour',
            category='natureza',
            province='huila',
            location_venue='Lubango',
            start_date=datetime.date(2026, 12, 10),
            price_aoa=25000,
            organizer_name='Destinos da Banda',
            description='Tour guiada',
            included_services=['Transporte 4x4', 'Guia Certificado'],
        )
        self.route = Route.objects.create(
            name='Rota do Sul',
            short_description='Lubango a Namibe',
            description='Descrição da rota',
            duration_days=3,
            difficulty='moderate',
            status='published',
        )

    def _attach_session_and_messages(self, request):
        request.user = self.staff
        request.session = self.client.session
        setattr(request, '_messages', FallbackStorage(request))
        return request

    def test_dashboard_home_renders_all_tabs(self):
        request = self._attach_session_and_messages(self.factory.get(reverse('dashboard:home')))
        response = dashboard_views.dashboard_home(request)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        self.assertIn('Jornadas Multi-Parceiro', html)
        self.assertIn('Especialidades de Guias', html)
        self.assertIn('Nova Reserva', html)

    def test_category_crud(self):
        # Create
        res = self.client.post(reverse('dashboard:category_add'), {
            'name': 'Praias',
            'icon': 'fas fa-umbrella-beach',
            'color': '#0077B6',
            'order': 2,
        })
        self.assertEqual(res.status_code, 302)
        cat = Category.objects.get(name='Praias')

        # Update
        res_edit = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'category', 'pk': cat.pk}),
            {
                'name': 'Praias & Costa',
                'icon': 'fas fa-water',
                'color': '#023E8A',
                'order': 3,
                'description': 'Litoral angolano',
            },
        )
        self.assertEqual(res_edit.status_code, 302)
        cat.refresh_from_db()
        self.assertEqual(cat.name, 'Praias & Costa')

        # Delete
        res_del = self.client.post(reverse('dashboard:category_delete', kwargs={'pk': cat.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=cat.pk).exists())

    def test_event_edit_form_and_crud(self):
        # GET edit view directly (ensures EventQuickForm.__init__ does not crash!)
        request = self._attach_session_and_messages(
            self.factory.get(reverse('dashboard:record_edit', kwargs={'model_key': 'event', 'pk': self.event.pk}))
        )
        response = dashboard_views.record_edit(request, 'event', self.event.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Transporte 4x4, Guia Certificado', response.content.decode('utf-8'))

        # POST update
        res = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'event', 'pk': self.event.pk}),
            {
                'title': 'Tour Serra da Leba Actualizada',
                'activity_type': 'tour',
                'category': 'natureza',
                'province': 'huila',
                'location_venue': 'Miradouro da Leba',
                'start_date': '2026-12-15',
                'price_aoa': '30000',
                'organizer_name': 'Destinos da Banda',
                'description': 'Descrição actualizada',
                'included_services': 'Transporte, Almoço, Seguro',
                'status': 'upcoming',
            },
        )
        self.assertEqual(res.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'Tour Serra da Leba Actualizada')
        self.assertEqual(self.event.included_services, ['Transporte', 'Almoço', 'Seguro'])

    def test_route_stop_crud(self):
        # Create
        res = self.client.post(reverse('dashboard:route_stop_add'), {
            'route': self.route.pk,
            'destination': self.destination.pk,
            'day': 1,
            'order': 1,
            'notes': 'Paragem inicial',
        })
        self.assertEqual(res.status_code, 302)
        stop = RouteStop.objects.get(route=self.route, destination=self.destination)

        # Update
        res_edit = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'route_stop', 'pk': stop.pk}),
            {
                'route': self.route.pk,
                'destination': self.destination.pk,
                'day': 2,
                'order': 3,
                'notes': 'Paragem actualizada',
            },
        )
        self.assertEqual(res_edit.status_code, 302)
        stop.refresh_from_db()
        self.assertEqual(stop.day, 2)
        self.assertEqual(stop.notes, 'Paragem actualizada')

        # Delete
        res_del = self.client.post(reverse('dashboard:route_stop_delete', kwargs={'pk': stop.pk}))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(RouteStop.objects.filter(pk=stop.pk).exists())

    def test_specialty_and_guide_crud(self):
        # Create Specialty
        res = self.client.post(reverse('dashboard:specialty_add'), {
            'nome': 'Ecoturismo',
            'icon': 'fas fa-leaf',
            'color': '#2D6A4F',
        })
        self.assertEqual(res.status_code, 302)
        esp = Especialidade.objects.get(nome='Ecoturismo')

        # Update Specialty
        res_edit = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'specialty', 'pk': esp.pk}),
            {'nome': 'Ecoturismo & Trilhos', 'icon': 'fas fa-mountain', 'color': '#1B4332'},
        )
        self.assertEqual(res_edit.status_code, 302)
        esp.refresh_from_db()
        self.assertEqual(esp.nome, 'Ecoturismo & Trilhos')

        # Create Guide with preco_dia_aoa
        res_g = self.client.post(reverse('dashboard:guide_add'), {
            'nome': 'Carlos Ndala',
            'provincia': 'huambo',
            'anos_experiencia': 5,
            'idiomas': 'pt, en',
            'especialidades': [esp.pk],
            'preco_dia_aoa': '55000',
            'biografia': 'Guia certificado no Planalto Central.',
            'activo': 'on',
        })
        self.assertEqual(res_g.status_code, 302)
        guide = GuiaTuristico.objects.get(nome='Carlos Ndala')
        self.assertEqual(float(guide.preco_dia_aoa), 55000.0)

        # Delete Guide & Specialty
        self.client.post(reverse('dashboard:guide_delete', kwargs={'pk': guide.pk}))
        self.client.post(reverse('dashboard:specialty_delete', kwargs={'pk': esp.pk}))
        self.assertFalse(GuiaTuristico.objects.filter(pk=guide.pk).exists())
        self.assertFalse(Especialidade.objects.filter(pk=esp.pk).exists())

    def test_room_type_toggle_and_accommodation_gps(self):
        res_acc = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'accommodation', 'pk': self.accommodation.pk}),
            {
                'name': 'Lodge do Planalto',
                'accommodation_type': 'lodge',
                'province': 'huambo',
                'city': 'Huambo',
                'latitude': '-12.776100',
                'longitude': '15.739200',
                'price_per_night_aoa': '50000',
                'short_description': 'Lodge confortável',
                'description': 'Descrição actualizada',
                'is_active': 'on',
            },
        )
        self.assertEqual(res_acc.status_code, 302)
        self.accommodation.refresh_from_db()
        self.assertIsNotNone(self.accommodation.latitude)

        rt = RoomType.objects.create(
            accommodation=self.accommodation,
            name='Suite Planalto',
            category='suite',
            price_per_night_aoa=60000,
            is_active=True,
        )
        self.client.post(reverse('dashboard:room_type_toggle', kwargs={'pk': rt.pk}))
        rt.refresh_from_db()
        self.assertFalse(rt.is_active)

    def test_booking_crud(self):
        # Create
        res = self.client.post(reverse('dashboard:booking_add'), {
            'accommodation': self.accommodation.pk,
            'units_reserved': 1,
            'guest_name': 'Ana Silva',
            'guest_email': 'ana@example.com',
            'guest_phone': '+244 923 111 222',
            'check_in': '2026-12-01',
            'check_out': '2026-12-04',
            'guests_count': 2,
            'status': 'pending',
        })
        self.assertEqual(res.status_code, 302)
        booking = Booking.objects.get(guest_name='Ana Silva')
        self.assertEqual(booking.total_nights, 3)

        # Update via record_edit
        res_edit = self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'booking', 'pk': booking.pk}),
            {
                'accommodation': self.accommodation.pk,
                'units_reserved': 2,
                'guest_name': 'Ana Maria Silva',
                'guest_email': 'ana@example.com',
                'guest_phone': '+244 923 111 222',
                'check_in': '2026-12-01',
                'check_out': '2026-12-03',
                'guests_count': 3,
                'status': 'confirmed',
            },
        )
        self.assertEqual(res_edit.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.guest_name, 'Ana Maria Silva')
        self.assertEqual(booking.status, 'confirmed')

        # Delete
        self.client.post(reverse('dashboard:booking_delete', kwargs={'pk': booking.pk}))
        self.assertFalse(Booking.objects.filter(pk=booking.pk).exists())

    def test_tour_booking_crud(self):
        res = self.client.post(reverse('dashboard:tour_booking_add'), {
            'event': self.event.pk,
            'participant_name': 'Pedro Costa',
            'participant_email': 'pedro@example.com',
            'participant_phone': '+244 923 222 333',
            'participants_count': 2,
            'status': 'confirmed',
        })
        self.assertEqual(res.status_code, 302)
        tb = EventBooking.objects.get(participant_name='Pedro Costa')

        # Update status
        self.client.post(reverse('dashboard:tour_booking_update_status', kwargs={'pk': tb.pk}), {'status': 'completed'})
        tb.refresh_from_db()
        self.assertEqual(tb.status, 'completed')

        # Update via record_edit
        self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'tour_booking', 'pk': tb.pk}),
            {
                'event': self.event.pk,
                'participant_name': 'Pedro Manuel Costa',
                'participant_email': 'pedro@example.com',
                'participant_phone': '+244 923 222 333',
                'participants_count': 3,
                'status': 'confirmed',
            },
        )
        tb.refresh_from_db()
        self.assertEqual(tb.participant_name, 'Pedro Manuel Costa')
        self.assertEqual(tb.participants_count, 3)

        # Delete
        self.client.post(reverse('dashboard:tour_booking_delete', kwargs={'pk': tb.pk}))
        self.assertFalse(EventBooking.objects.filter(pk=tb.pk).exists())

    def test_visit_booking_crud(self):
        res = self.client.post(reverse('dashboard:visit_booking_add'), {
            'destination': self.destination.pk,
            'visitor_name': 'Sofia Mendes',
            'visitor_email': 'sofia@example.com',
            'visitor_phone': '+244 923 444 555',
            'visit_date': '2026-12-20',
            'participants_count': 4,
            'status': 'confirmed',
        })
        self.assertEqual(res.status_code, 302)
        vb = DestinationVisitBooking.objects.get(visitor_name='Sofia Mendes')

        # Update status
        self.client.post(reverse('dashboard:visit_booking_update_status', kwargs={'pk': vb.pk}), {'status': 'completed'})
        vb.refresh_from_db()
        self.assertEqual(vb.status, 'completed')

        # Delete
        self.client.post(reverse('dashboard:visit_booking_delete', kwargs={'pk': vb.pk}))
        self.assertFalse(DestinationVisitBooking.objects.filter(pk=vb.pk).exists())

    def test_trip_order_crud(self):
        res = self.client.post(reverse('dashboard:trip_order_add'), {
            'province': 'huambo',
            'guest_name': 'Manuel Domingos',
            'guest_email': 'manuel@example.com',
            'guest_phone': '+244 923 777 888',
            'start_date': '2026-12-05',
            'end_date': '2026-12-08',
            'travelers_count': 2,
            'payment_method': 'mcx_express',
            'payment_status': 'paid',
            'total_aoa': '180000',
            'status': 'pending',
        })
        self.assertEqual(res.status_code, 302)
        order = TripOrder.objects.get(guest_name='Manuel Domingos')

        # Update status
        self.client.post(reverse('dashboard:trip_order_update_status', kwargs={'pk': order.pk}), {'status': 'confirmed'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

        # Update via record_edit
        self.client.post(
            reverse('dashboard:record_edit', kwargs={'model_key': 'trip_order', 'pk': order.pk}),
            {
                'province': 'huila',
                'guest_name': 'Manuel Domingos Jr.',
                'guest_email': 'manuel@example.com',
                'guest_phone': '+244 923 777 888',
                'start_date': '2026-12-05',
                'end_date': '2026-12-09',
                'travelers_count': 4,
                'payment_method': 'referencia_mcx',
                'payment_status': 'paid',
                'total_aoa': '250000',
                'status': 'completed',
            },
        )
        order.refresh_from_db()
        self.assertEqual(order.guest_name, 'Manuel Domingos Jr.')
        self.assertEqual(order.status, 'completed')

        # Delete
        self.client.post(reverse('dashboard:trip_order_delete', kwargs={'pk': order.pk}))
        self.assertFalse(TripOrder.objects.filter(pk=order.pk).exists())

    def test_booking_and_trip_order_form_date_validation(self):
        bad_booking = BookingForm(data={
            'accommodation': self.accommodation.pk,
            'units_reserved': 1,
            'guest_name': 'Teste',
            'guest_email': 'teste@example.com',
            'guest_phone': '+244 900 000 000',
            'check_in': '2026-12-10',
            'check_out': '2026-12-08',
            'guests_count': 1,
            'status': 'pending',
        })
        self.assertFalse(bad_booking.is_valid())
        self.assertIn('check_out', bad_booking.errors)

        bad_order = TripOrderForm(data={
            'province': 'luanda',
            'guest_name': 'Teste',
            'guest_email': 'teste@example.com',
            'guest_phone': '+244 900 000 000',
            'start_date': '2026-12-10',
            'end_date': '2026-12-05',
            'travelers_count': 2,
            'payment_method': 'mcx_express',
            'payment_status': 'awaiting',
            'total_aoa': '10000',
            'status': 'pending',
        })
        self.assertFalse(bad_order.is_valid())
        self.assertIn('end_date', bad_order.errors)

    def test_non_staff_blocked_from_new_crud_endpoints(self):
        self.client.force_login(self.normal_user)
        for url in [
            reverse('dashboard:booking_add'),
            reverse('dashboard:tour_booking_add'),
            reverse('dashboard:visit_booking_add'),
            reverse('dashboard:trip_order_add'),
            reverse('dashboard:specialty_add'),
        ]:
            res = self.client.post(url, {})
            self.assertEqual(res.status_code, 302)
            self.assertIn(reverse('dashboard:login'), res['Location'])

    def test_all_seven_quick_action_pages_render_and_support_full_crud(self):
        # 1. Verificar que cada uma das 7 abas abre directamente via ?tab=...
        for tab in ('destinations', 'accommodations', 'routes', 'events', 'articles', 'gallery', 'guides'):
            req = self._attach_session_and_messages(
                self.factory.get(f"{reverse('dashboard:home')}?tab={tab}")
            )
            res = dashboard_views.dashboard_home(req)
            self.assertEqual(res.status_code, 200)
            html = res.content.decode('utf-8')
            self.assertIn(f'class="tab-pane fade show active" id="tab-{tab}"', html)

        # 2. Categoria usando apenas os campos do formulário do template (name + icon)
        res_cat = self.client.post(reverse('dashboard:category_add'), {
            'name': 'Cultura Viva',
            'icon': 'fas fa-masks-theater',
        })
        self.assertEqual(res_cat.status_code, 302)
        self.assertTrue(Category.objects.filter(name='Cultura Viva').exists())

        # 3. Destino CRUD
        self.client.post(reverse('dashboard:destination_add'), {
            'name': 'Fenda da Tundavala',
            'category': self.category.pk,
            'province': 'huila',
            'short_description': 'Miradouro espectacular',
            'description': 'Descrição completa da Fenda da Tundavala',
            'status': 'published',
        })
        dest = Destination.objects.get(name='Fenda da Tundavala')
        self.client.post(reverse('dashboard:destination_toggle', kwargs={'pk': dest.pk}), {'field': 'status'})
        dest.refresh_from_db()
        self.assertEqual(dest.status, 'draft')
        self.client.post(reverse('dashboard:destination_delete', kwargs={'pk': dest.pk}))
        self.assertFalse(Destination.objects.filter(pk=dest.pk).exists())

        # 4. Artigo Cultural CRUD
        self.client.post(reverse('dashboard:article_add'), {
            'title': 'História do Bailundo',
            'topic': 'historia',
            'province': 'huambo',
            'author_name': 'Redacção',
            'reading_time_minutes': 5,
            'summary': 'Resumo editorial',
            'content': 'Conteúdo histórico detalhado.',
            'status': 'published',
        })
        art = CulturalArticle.objects.get(title='História do Bailundo')
        self.client.post(reverse('dashboard:article_toggle', kwargs={'pk': art.pk}))
        art.refresh_from_db()
        self.assertEqual(art.status, 'draft')
        self.client.post(reverse('dashboard:article_delete', kwargs={'pk': art.pk}))
        self.assertFalse(CulturalArticle.objects.filter(pk=art.pk).exists())

        # 5. Galeria CRUD
        first_item_type = GalleryItem.ITEM_TYPE_CHOICES[0][0]
        first_cat = GalleryItem.CATEGORY_CHOICES[0][0]
        self.client.post(reverse('dashboard:gallery_add'), {
            'title': 'Pôr do Sol no Namibe',
            'item_type': first_item_type,
            'category': first_cat,
            'province': 'namibe',
            'location_name': 'Moçâmedes',
            'description': 'Fotografia da costa do Namibe',
        })
        gal = GalleryItem.objects.get(title='Pôr do Sol no Namibe')
        self.client.post(reverse('dashboard:gallery_toggle', kwargs={'pk': gal.pk}))
        gal.refresh_from_db()
        self.assertTrue(gal.is_featured)
        self.client.post(reverse('dashboard:gallery_delete', kwargs={'pk': gal.pk}))
        self.assertFalse(GalleryItem.objects.filter(pk=gal.pk).exists())

