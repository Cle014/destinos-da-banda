import datetime
import logging

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django.urls import reverse

from apps.gallery.models import GalleryItem
from apps.routes.models import Route, RouteStop
from apps.accommodations.models import Accommodation, RoomType, Booking, TripOrder
from apps.destinations.models import Destination, Category, CulturalArticle, DestinationVisitBooking
from apps.events.models import Event, EventBooking
from apps.guides.models import GuiaTuristico, Especialidade

from .forms import (
    CategoryForm,
    DestinationQuickForm,
    GalleryItemForm,
    RouteForm,
    RouteStopForm,
    AccommodationForm,
    RoomTypeForm,
    EventQuickForm,
    GuideForm,
    CulturalArticleForm,
    EspecialidadeForm,
    BookingForm,
    EventBookingForm,
    DestinationVisitBookingForm,
    TripOrderForm,
)

security_log = logging.getLogger('apps.dashboard.security')


def is_admin_or_staff(user):
    return user.is_authenticated and user.is_active and (user.is_staff or user.is_superuser)


# ---------------------------------------------------------------------------
# Protecção contra força bruta
# ---------------------------------------------------------------------------

def _client_ip(request):
    return request.META.get('REMOTE_ADDR', 'unknown')


def _throttle_keys(ip, username):
    return (f'dash-login:ip:{ip}', f'dash-login:ipuser:{ip}:{username.lower()}')


def _is_locked(ip, username):
    ip_key, pair_key = _throttle_keys(ip, username)
    return (
        (cache.get(pair_key) or 0) >= settings.DASHBOARD_LOGIN_MAX_ATTEMPTS
        or (cache.get(ip_key) or 0) >= settings.DASHBOARD_LOGIN_MAX_ATTEMPTS_PER_IP
    )


def _register_failure(ip, username):
    timeout = settings.DASHBOARD_LOGIN_LOCKOUT_SECONDS
    for key in _throttle_keys(ip, username):
        if cache.add(key, 1, timeout):
            continue
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout)


def _clear_failures(ip, username):
    cache.delete(_throttle_keys(ip, username)[1])


def _safe_next(request, candidate):
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return reverse('dashboard:home')


@sensitive_post_parameters('password')
@csrf_protect
@never_cache
def dashboard_login(request):
    """Início de sessão no Painel de Gestão."""
    next_url = _safe_next(request, request.POST.get('next') or request.GET.get('next'))

    if is_admin_or_staff(request.user):
        return redirect(next_url)

    error_message = None
    status = 200

    if request.method == 'POST':
        ip = _client_ip(request)
        u = request.POST.get('username', '').strip()[:150]
        p = request.POST.get('password', '')

        if _is_locked(ip, u):
            security_log.warning('Login bloqueado ip=%s user=%s', ip, u)
            minutes = settings.DASHBOARD_LOGIN_LOCKOUT_SECONDS // 60
            error_message = f"Demasiadas tentativas falhadas. Tente novamente dentro de {minutes} minutos."
            status = 429
        else:
            user = authenticate(request, username=u, password=p)
            if user is not None and is_admin_or_staff(user):
                _clear_failures(ip, u)
                login(request, user)
                request.session.set_expiry(settings.STAFF_SESSION_IDLE_TIMEOUT)
                security_log.info('Login no painel ip=%s user=%s', ip, user.username)
                return redirect(next_url)
            _register_failure(ip, u)
            security_log.warning('Login falhado ip=%s user=%s', ip, u)
            error_message = "Credenciais inválidas."

    return render(request, 'dashboard/login.html', {
        'error_message': error_message,
        'next_url': next_url,
    }, status=status)


@require_POST
def dashboard_logout(request):
    """Encerra a sessão do painel (apenas POST com token CSRF)."""
    logout(request)
    messages.info(request, "Sessão terminada com sucesso.")
    return redirect('core:home')


# ---------------------------------------------------------------------------
# Painel Principal
# ---------------------------------------------------------------------------

VALID_TABS = {
    'overview', 'bookings', 'destinations', 'accommodations',
    'routes', 'events', 'articles', 'gallery', 'guides',
}


@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def dashboard_home(request):
    """Página principal do Painel de Gestão da Plataforma + Painel de Densidade (Fase 2.6)."""
    active_tab = request.GET.get('tab', 'overview')
    if active_tab not in VALID_TABS:
        active_tab = 'overview'

    bookings_direct_total = Booking.objects.count()
    bookings_direct_completed = Booking.objects.filter(status='completed').count()
    trip_orders_total = TripOrder.objects.count()
    trip_orders_completed = TripOrder.objects.filter(status='completed').count()
    trip_orders_partial = TripOrder.objects.filter(status='partial_failure').count()

    combined_orders_total = bookings_direct_total + trip_orders_total
    combined_completed = bookings_direct_completed + trip_orders_completed
    completion_rate = round((combined_completed / combined_orders_total) * 100, 1) if combined_orders_total > 0 else 0.0

    min_threshold = getattr(settings, 'MIN_MODULE_ITEMS_PER_PROVINCE', 5)
    stale_days = getattr(settings, 'STALE_RECORD_DAYS', 60)
    stale_cutoff = timezone.now() - datetime.timedelta(days=stale_days)

    # Matriz de Densidade por Província (Parceiros & Fichas Activas vs. Limiar da Cunha)
    province_density = []
    for prov_code, prov_label in Destination.PROVINCE_CHOICES:
        d_cnt = Destination.objects.filter(status='published', province=prov_code).count()
        a_cnt = Accommodation.objects.filter(is_active=True, province=prov_code).count()
        g_cnt = GuiaTuristico.objects.filter(activo=True, provincia=prov_code).count()
        e_cnt = Event.objects.filter(province=prov_code).count()
        gal_cnt = GalleryItem.objects.filter(province=prov_code).count()
        total_partners = d_cnt + a_cnt + g_cnt + e_cnt

        if total_partners > 0 or prov_code in ('huambo', 'luanda', 'huila', 'benguela'):
            ready_modules = sum(1 for c in (d_cnt, a_cnt, g_cnt, e_cnt, gal_cnt) if c >= min_threshold)
            province_density.append({
                'code': prov_code,
                'label': prov_label,
                'destinations': d_cnt,
                'accommodations': a_cnt,
                'guides': g_cnt,
                'events': e_cnt,
                'gallery': gal_cnt,
                'total_partners': total_partners,
                'ready_modules': ready_modules,
                'wedge_active': ready_modules >= 3,
            })

    # Fichas Desactualizadas ou Incompletas (updated_at < stale_cutoff ou sem coordenadas/preço)
    stale_records = []
    for d in Destination.objects.all():
        reasons = []
        if d.updated_at < stale_cutoff:
            reasons.append(f"Sem actualização há + de {stale_days} dias")
        if not d.has_coordinates:
            reasons.append("Sem coordenadas GPS")
        if reasons:
            stale_records.append({
                'type': 'Destino',
                'model_key': 'destination',
                'pk': d.pk,
                'name': d.name,
                'province': d.get_province_display(),
                'updated_at': d.updated_at,
                'reasons': ', '.join(reasons),
            })

    for a in Accommodation.objects.all():
        reasons = []
        if a.latitude is None or a.longitude is None:
            reasons.append("Sem coordenadas GPS para o Planeador")
        if a.price_per_night_aoa <= 0:
            reasons.append("Sem preço em Kz")
        if reasons:
            stale_records.append({
                'type': 'Alojamento',
                'model_key': 'accommodation',
                'pk': a.pk,
                'name': a.name,
                'province': a.get_province_display(),
                'updated_at': a.created_at,
                'reasons': ', '.join(reasons),
            })

    for g in GuiaTuristico.objects.all():
        reasons = []
        if g.updated_at < stale_cutoff:
            reasons.append(f"Sem actualização há + de {stale_days} dias")
        if not g.preco_dia_aoa or g.preco_dia_aoa <= 0:
            reasons.append("Sem tarifa em Kz")
        if reasons:
            stale_records.append({
                'type': 'Guia',
                'model_key': 'guide',
                'pk': g.pk,
                'name': g.nome,
                'province': g.get_provincia_display(),
                'updated_at': g.updated_at,
                'reasons': ', '.join(reasons),
            })

    metrics = {
        'destinations': Destination.objects.count(),
        'destinations_published': Destination.objects.filter(status='published').count(),
        'categories': Category.objects.count(),
        'accommodations': Accommodation.objects.count(),
        'accommodations_active': Accommodation.objects.filter(is_active=True).count(),
        'routes': Route.objects.count(),
        'gallery': GalleryItem.objects.count(),
        'events': Event.objects.count(),
        'guides': GuiaTuristico.objects.count(),
        'articles': CulturalArticle.objects.count(),
        'room_types': RoomType.objects.count(),
        'tour_bookings': EventBooking.objects.count(),
        'visit_bookings': DestinationVisitBooking.objects.count(),
        'bookings_total': combined_orders_total,
        'bookings_pending': Booking.objects.filter(status='pending').count() + TripOrder.objects.filter(status='pending').count(),
        'bookings_confirmed': Booking.objects.filter(status='confirmed').count() + TripOrder.objects.filter(status='confirmed').count(),
        'bookings_completed': combined_completed,
        'trip_orders_total': trip_orders_total,
        'trip_orders_partial': trip_orders_partial,
        'completion_rate': completion_rate,
        'stale_count': len(stale_records),
        'min_threshold': min_threshold,
    }

    recent_bookings = Booking.objects.select_related('accommodation').order_by('-created_at')[:50]
    recent_trip_orders = TripOrder.objects.prefetch_related('items').order_by('-created_at')[:50]
    destinations = Destination.objects.select_related('category').order_by('-is_featured', '-created_at')
    categories = Category.objects.order_by('order', 'name')
    accommodations = Accommodation.objects.order_by('-is_featured', '-created_at')
    routes = Route.objects.prefetch_related('stops__destination').order_by('-is_featured', '-created_at')
    events = Event.objects.order_by('-is_featured', 'start_date')
    gallery_items = GalleryItem.objects.order_by('-is_featured', 'order', '-created_at')
    guides = GuiaTuristico.objects.prefetch_related('especialidades', 'destinos').order_by('-destaque', '-created_at')
    specialties = Especialidade.objects.order_by('nome')

    context = {
        'active_tab': active_tab,
        'metrics': metrics,
        'province_density': province_density,
        'stale_records': stale_records,
        'recent_bookings': recent_bookings,
        'recent_trip_orders': recent_trip_orders,
        'destinations': destinations,
        'categories': categories,
        'accommodations': accommodations,
        'routes': routes,
        'events': events,
        'gallery_items': gallery_items,
        'guides': guides,
        'specialties': specialties,
        'destination_form': DestinationQuickForm(),
        'category_form': CategoryForm(),
        'accommodation_form': AccommodationForm(),
        'route_form': RouteForm(),
        'route_stop_form': RouteStopForm(),
        'event_form': EventQuickForm(),
        'gallery_form': GalleryItemForm(),
        'guide_form': GuideForm(),
        'specialty_form': EspecialidadeForm(),
        'room_type_form': RoomTypeForm(),
        'article_form': CulturalArticleForm(),
        'booking_form': BookingForm(),
        'tour_booking_form': EventBookingForm(),
        'visit_booking_form': DestinationVisitBookingForm(),
        'trip_order_form': TripOrderForm(),
        'room_types': RoomType.objects.select_related('accommodation').all(),
        'articles': CulturalArticle.objects.select_related('destination', 'related_tour').all(),
        'tour_bookings': EventBooking.objects.select_related('event').order_by('-created_at')[:50],
        'visit_bookings': DestinationVisitBooking.objects.select_related('destination').order_by('-created_at')[:50],
    }
    return render(request, 'dashboard/dashboard.html', context)


# ---------------------------------------------------------------------------
# Edição Unificada de Qualquer Registo
# ---------------------------------------------------------------------------

EDIT_REGISTRY = {
    'destination': (Destination, DestinationQuickForm, 'Destino Turístico', 'destinations'),
    'category': (Category, CategoryForm, 'Categoria de Destino', 'destinations'),
    'accommodation': (Accommodation, AccommodationForm, 'Alojamento', 'accommodations'),
    'route': (Route, RouteForm, 'Rota Turística', 'routes'),
    'route_stop': (RouteStop, RouteStopForm, 'Paragem de Rota', 'routes'),
    'event': (Event, EventQuickForm, 'Evento / Actividade', 'events'),
    'gallery': (GalleryItem, GalleryItemForm, 'Item da Galeria', 'gallery'),
    'guide': (GuiaTuristico, GuideForm, 'Guia Turístico', 'guides'),
    'specialty': (Especialidade, EspecialidadeForm, 'Especialidade de Guia', 'guides'),
    'room_type': (RoomType, RoomTypeForm, 'Tipologia de Quarto / Suite', 'accommodations'),
    'article': (CulturalArticle, CulturalArticleForm, 'Artigo Cultural (Blog)', 'articles'),
    'booking': (Booking, BookingForm, 'Reserva de Alojamento', 'bookings'),
    'tour_booking': (EventBooking, EventBookingForm, 'Inscrição em Tour / Evento', 'bookings'),
    'visit_booking': (DestinationVisitBooking, DestinationVisitBookingForm, 'Reserva de Visita / Agroturismo', 'bookings'),
    'trip_order': (TripOrder, TripOrderForm, 'Jornada Multi-Parceiro', 'bookings'),
}


@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def record_edit(request, model_key, pk):
    if model_key not in EDIT_REGISTRY:
        messages.error(request, "Tipo de registo inválido.")
        return redirect('dashboard:home')

    model_cls, form_cls, label, return_tab = EDIT_REGISTRY[model_key]
    instance = get_object_or_404(model_cls, pk=pk)

    if request.method == 'POST':
        form = form_cls(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{label} '{obj}' actualizado com sucesso!")
            return redirect(f"{reverse('dashboard:home')}?tab={return_tab}")
        messages.error(request, f"Verifique os campos assinalados: {form.errors.as_text()}")
    else:
        form = form_cls(instance=instance)

    return render(request, 'dashboard/edit.html', {
        'form': form,
        'instance': instance,
        'model_key': model_key,
        'model_label': label,
        'return_tab': return_tab,
    })


# ---------------------------------------------------------------------------
# Destinos & Categorias
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def destination_add(request):
    form = DestinationQuickForm(request.POST, request.FILES)
    if form.is_valid():
        dest = form.save()
        messages.success(request, f"Destino '{dest.name}' publicado com sucesso!")
    else:
        messages.error(request, f"Erro ao adicionar destino: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=destinations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def destination_delete(request, pk):
    dest = get_object_or_404(Destination, pk=pk)
    name = dest.name
    dest.delete()
    messages.success(request, f"Destino '{name}' eliminado.")
    return redirect(f"{reverse('dashboard:home')}?tab=destinations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def destination_toggle(request, pk):
    dest = get_object_or_404(Destination, pk=pk)
    field = request.POST.get('field', 'status')
    if field == 'featured':
        dest.is_featured = not dest.is_featured
        dest.save(update_fields=['is_featured'])
        messages.success(request, f"Destaque de '{dest.name}' actualizado.")
    else:
        dest.status = 'draft' if dest.status == 'published' else 'published'
        dest.save(update_fields=['status'])
        messages.success(request, f"Estado de '{dest.name}' alterado para {dest.get_status_display()}.")
    return redirect(f"{reverse('dashboard:home')}?tab=destinations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def category_add(request):
    form = CategoryForm(request.POST)
    if form.is_valid():
        cat = form.save()
        messages.success(request, f"Categoria '{cat.name}' criada!")
    else:
        messages.error(request, f"Erro ao criar categoria: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=destinations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    name = cat.name
    cat.delete()
    messages.success(request, f"Categoria '{name}' removida.")
    return redirect(f"{reverse('dashboard:home')}?tab=destinations")


# ---------------------------------------------------------------------------
# Galeria
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def gallery_add(request):
    form = GalleryItemForm(request.POST, request.FILES)
    if form.is_valid():
        item = form.save()
        messages.success(request, f"Imagem '{item.title}' adicionada à Galeria!")
    else:
        messages.error(request, f"Erro ao adicionar imagem: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=gallery")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def gallery_delete(request, pk):
    item = get_object_or_404(GalleryItem, pk=pk)
    title = item.title
    item.delete()
    messages.success(request, f"Item '{title}' removido da galeria.")
    return redirect(f"{reverse('dashboard:home')}?tab=gallery")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def gallery_toggle(request, pk):
    item = get_object_or_404(GalleryItem, pk=pk)
    item.is_featured = not item.is_featured
    item.save(update_fields=['is_featured'])
    messages.success(request, f"Destaque de '{item.title}' actualizado.")
    return redirect(f"{reverse('dashboard:home')}?tab=gallery")


# ---------------------------------------------------------------------------
# Rotas & Paragens
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def route_add(request):
    form = RouteForm(request.POST, request.FILES)
    if form.is_valid():
        route = form.save()
        messages.success(request, f"Rota '{route.name}' criada com sucesso!")
    else:
        messages.error(request, f"Erro ao criar rota: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=routes")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def route_delete(request, pk):
    route = get_object_or_404(Route, pk=pk)
    name = route.name
    route.delete()
    messages.success(request, f"Rota '{name}' removida.")
    return redirect(f"{reverse('dashboard:home')}?tab=routes")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def route_toggle(request, pk):
    route = get_object_or_404(Route, pk=pk)
    field = request.POST.get('field', 'status')
    if field == 'featured':
        route.is_featured = not route.is_featured
        route.save(update_fields=['is_featured'])
    else:
        route.status = 'draft' if route.status == 'published' else 'published'
        route.save(update_fields=['status'])
    messages.success(request, f"Rota '{route.name}' actualizada.")
    return redirect(f"{reverse('dashboard:home')}?tab=routes")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def route_stop_add(request):
    form = RouteStopForm(request.POST)
    if form.is_valid():
        stop = form.save()
        messages.success(request, f"Paragem '{stop.destination.name}' adicionada à rota '{stop.route.name}'!")
    else:
        messages.error(request, f"Erro ao adicionar paragem: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=routes")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def route_stop_delete(request, pk):
    stop = get_object_or_404(RouteStop, pk=pk)
    stop.delete()
    messages.success(request, "Paragem removida da rota.")
    return redirect(f"{reverse('dashboard:home')}?tab=routes")


# ---------------------------------------------------------------------------
# Alojamentos & Reservas
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def accommodation_add(request):
    form = AccommodationForm(request.POST, request.FILES)
    if form.is_valid():
        acc = form.save()
        messages.success(request, f"Alojamento '{acc.name}' cadastrado com sucesso!")
    else:
        messages.error(request, f"Erro ao cadastrar alojamento: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def accommodation_delete(request, pk):
    acc = get_object_or_404(Accommodation, pk=pk)
    name = acc.name
    acc.delete()
    messages.success(request, f"Alojamento '{name}' removido.")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def accommodation_toggle(request, pk):
    acc = get_object_or_404(Accommodation, pk=pk)
    field = request.POST.get('field', 'active')
    if field == 'featured':
        acc.is_featured = not acc.is_featured
        acc.save(update_fields=['is_featured'])
    else:
        acc.is_active = not acc.is_active
        acc.save(update_fields=['is_active'])
    messages.success(request, f"Alojamento '{acc.name}' actualizado.")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def booking_add(request):
    form = BookingForm(request.POST)
    if form.is_valid():
        booking = form.save()
        messages.success(request, f"Reserva #{booking.reference_code} criada para '{booking.guest_name}'!")
    else:
        messages.error(request, f"Erro ao criar reserva: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def booking_update_status(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Booking.STATUS_CHOICES):
        booking.status = new_status
        booking.save(update_fields=['status'])
        messages.success(request, f"Reserva #{booking.reference_code} actualizada para '{booking.get_status_display()}'.")
    else:
        messages.error(request, "Estado de reserva inválido.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    ref = booking.reference_code
    booking.delete()
    messages.success(request, f"Reserva #{ref} eliminada.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


# ---------------------------------------------------------------------------
# Eventos & Actividades
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def event_add(request):
    form = EventQuickForm(request.POST, request.FILES)
    if form.is_valid():
        ev = form.save()
        messages.success(request, f"Evento '{ev.title}' adicionado com sucesso!")
    else:
        messages.error(request, f"Erro ao adicionar evento: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=events")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def event_delete(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    title = ev.title
    ev.delete()
    messages.success(request, f"Evento '{title}' eliminado.")
    return redirect(f"{reverse('dashboard:home')}?tab=events")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def event_toggle(request, pk):
    ev = get_object_or_404(Event, pk=pk)
    ev.is_featured = not ev.is_featured
    ev.save(update_fields=['is_featured'])
    messages.success(request, f"Destaque de '{ev.title}' actualizado.")
    return redirect(f"{reverse('dashboard:home')}?tab=events")


# ---------------------------------------------------------------------------
# Guias Turísticos
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def guide_add(request):
    form = GuideForm(request.POST, request.FILES)
    if form.is_valid():
        g = form.save()
        messages.success(request, f"Guia '{g.nome}' registado com sucesso!")
    else:
        messages.error(request, f"Erro ao registar guia: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=guides")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def guide_delete(request, pk):
    g = get_object_or_404(GuiaTuristico, pk=pk)
    nome = g.nome
    g.delete()
    messages.success(request, f"Guia '{nome}' removido.")
    return redirect(f"{reverse('dashboard:home')}?tab=guides")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def guide_toggle(request, pk):
    g = get_object_or_404(GuiaTuristico, pk=pk)
    field = request.POST.get('field', 'activo')
    if field == 'verificado':
        g.verificado = not g.verificado
        g.save(update_fields=['verificado'])
    elif field == 'destaque':
        g.destaque = not g.destaque
        g.save(update_fields=['destaque'])
    else:
        g.activo = not g.activo
        g.save(update_fields=['activo'])
    messages.success(request, f"Guia '{g.nome}' actualizado.")
    return redirect(f"{reverse('dashboard:home')}?tab=guides")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def specialty_add(request):
    form = EspecialidadeForm(request.POST)
    if form.is_valid():
        esp = form.save()
        messages.success(request, f"Especialidade '{esp.nome}' criada!")
    else:
        messages.error(request, f"Erro ao criar especialidade: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=guides")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def specialty_delete(request, pk):
    esp = get_object_or_404(Especialidade, pk=pk)
    nome = esp.nome
    esp.delete()
    messages.success(request, f"Especialidade '{nome}' removida.")
    return redirect(f"{reverse('dashboard:home')}?tab=guides")


# ---------------------------------------------------------------------------
# Tipologias de Quartos & Suites (Hotelaria)
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def room_type_add(request):
    form = RoomTypeForm(request.POST, request.FILES)
    if form.is_valid():
        rt = form.save()
        messages.success(request, f"Tipologia '{rt.name}' adicionada a '{rt.accommodation.name}'!")
    else:
        messages.error(request, f"Erro ao adicionar tipologia: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def room_type_delete(request, pk):
    rt = get_object_or_404(RoomType, pk=pk)
    name = rt.name
    rt.delete()
    messages.success(request, f"Tipologia '{name}' removida.")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def room_type_toggle(request, pk):
    rt = get_object_or_404(RoomType, pk=pk)
    rt.is_active = not rt.is_active
    rt.save(update_fields=['is_active'])
    messages.success(request, f"Tipologia '{rt.name}' actualizada.")
    return redirect(f"{reverse('dashboard:home')}?tab=accommodations")


# ---------------------------------------------------------------------------
# Blog Cultural — Artigos Editoriais
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def article_add(request):
    form = CulturalArticleForm(request.POST, request.FILES)
    if form.is_valid():
        art = form.save()
        messages.success(request, f"Artigo cultural '{art.title}' publicado com sucesso!")
    else:
        messages.error(request, f"Erro ao publicar artigo: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=articles")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def article_delete(request, pk):
    art = get_object_or_404(CulturalArticle, pk=pk)
    title = art.title
    art.delete()
    messages.success(request, f"Artigo '{title}' eliminado.")
    return redirect(f"{reverse('dashboard:home')}?tab=articles")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def article_toggle(request, pk):
    art = get_object_or_404(CulturalArticle, pk=pk)
    art.status = 'draft' if art.status == 'published' else 'published'
    art.save(update_fields=['status'])
    messages.success(request, f"Estado do artigo '{art.title}' alterado para {art.get_status_display()}.")
    return redirect(f"{reverse('dashboard:home')}?tab=articles")


# ---------------------------------------------------------------------------
# Gestão de Inscrições em Tours, Visitas de Agroturismo e Jornadas
# ---------------------------------------------------------------------------

@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def tour_booking_add(request):
    form = EventBookingForm(request.POST)
    if form.is_valid():
        tb = form.save()
        messages.success(request, f"Inscrição de Tour #{tb.reference_code} criada para '{tb.participant_name}'!")
    else:
        messages.error(request, f"Erro ao criar inscrição de tour: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def tour_booking_update_status(request, pk):
    tb = get_object_or_404(EventBooking, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(EventBooking.STATUS_CHOICES):
        tb.status = new_status
        tb.save(update_fields=['status'])
        messages.success(request, f"Inscrição de Tour #{tb.reference_code} actualizada para '{tb.get_status_display()}'.")
    else:
        messages.error(request, "Estado de inscrição inválido.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def tour_booking_delete(request, pk):
    tb = get_object_or_404(EventBooking, pk=pk)
    ref = tb.reference_code
    tb.delete()
    messages.success(request, f"Inscrição de Tour #{ref} eliminada.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def visit_booking_add(request):
    form = DestinationVisitBookingForm(request.POST)
    if form.is_valid():
        vb = form.save()
        messages.success(request, f"Reserva de Visita #{vb.reference_code} criada para '{vb.visitor_name}'!")
    else:
        messages.error(request, f"Erro ao criar reserva de visita: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def visit_booking_update_status(request, pk):
    vb = get_object_or_404(DestinationVisitBooking, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(DestinationVisitBooking.STATUS_CHOICES):
        vb.status = new_status
        vb.save(update_fields=['status'])
        messages.success(request, f"Reserva de Visita #{vb.reference_code} actualizada para '{vb.get_status_display()}'.")
    else:
        messages.error(request, "Estado de reserva de visita inválido.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def visit_booking_delete(request, pk):
    vb = get_object_or_404(DestinationVisitBooking, pk=pk)
    ref = vb.reference_code
    vb.delete()
    messages.success(request, f"Reserva de Visita #{ref} eliminada.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def trip_order_add(request):
    form = TripOrderForm(request.POST)
    if form.is_valid():
        order = form.save()
        messages.success(request, f"Jornada #{order.reference_code} criada para '{order.guest_name}'!")
    else:
        messages.error(request, f"Erro ao criar jornada: {form.errors.as_text()}")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def trip_order_update_status(request, pk):
    order = get_object_or_404(TripOrder, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(TripOrder.STATUS_CHOICES):
        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(request, f"Jornada #{order.reference_code} actualizada para '{order.get_status_display()}'.")
    else:
        messages.error(request, "Estado de jornada inválido.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")


@require_POST
@user_passes_test(is_admin_or_staff, login_url='dashboard:login')
def trip_order_delete(request, pk):
    order = get_object_or_404(TripOrder, pk=pk)
    ref = order.reference_code
    order.delete()
    messages.success(request, f"Jornada #{ref} eliminada.")
    return redirect(f"{reverse('dashboard:home')}?tab=bookings")
