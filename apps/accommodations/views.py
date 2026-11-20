import datetime
import re
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Avg, Q
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Accommodation, RoomType, Booking, AccommodationReview, TripOrderItem

PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,30}$')

FALLBACK_ACCOMMODATIONS = [
    {
        'id': 1,
        'name': 'Hotel Ekuikui I — Cidade Alta do Huambo',
        'slug': 'hotel-ekuikui-huambo',
        'accommodation_type': 'hotel',
        'accommodation_type_label': 'Hotel',
        'province': 'huambo',
        'province_label': 'Huambo',
        'city': 'Cidade Alta, Huambo',
        'address': 'Avenida da Independência, Cidade Alta, Huambo',
        'short_description': 'Hotel de referência no Planalto Central com suites executivas, restaurante de gastronomia angolana e internacional e salas de conferência.',
        'description': 'Situado na nobre Cidade Alta do Huambo, o Hotel Ekuikui oferece conforto moderno, climatização central, Wi-Fi de alta velocidade e fácil acesso ao Jardim da Cultura.',
        'price_per_night_aoa': 95000,
        'formatted_price_aoa': '95 000 Kz',
        'formatted_price_range_aoa': '95 000 Kz – 145 000 Kz',
        'price_per_night_usd': 110,
        'rating': 4.8,
        'review_count': 118,
        'max_guests': 3,
        'bedrooms': 1,
        'bathrooms': 1,
        'amenities': ['wifi', 'ar_condicionado', 'pequeno_almoco', 'restaurante', 'estacionamento', 'seguranca_24h'],
        'display_image': 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1000&q=80',
        'contact_phone': '+244 923 410 100',
        'contact_whatsapp': '+244923410100',
        'is_featured': True,
        'is_verified': True,
        'verification_criteria': 'Licença Hoteleira INFOTUR, NIF e vistoria presencial no Huambo',
        'is_demo': False,
    },
]


def _parse_dates_with_defaults(check_in_str, check_out_str):
    today = datetime.date.today()
    default_in = today + datetime.timedelta(days=1)
    default_out = today + datetime.timedelta(days=3)
    try:
        c_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date() if check_in_str else default_in
    except ValueError:
        c_in = default_in
    try:
        c_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date() if check_out_str else default_out
    except ValueError:
        c_out = default_out
    if c_out <= c_in:
        c_out = c_in + datetime.timedelta(days=2)
    return c_in, c_out


def accommodation_list(request):
    selected_type = request.GET.get('type', '').strip()
    selected_model = request.GET.get('mode', '').strip()  # 'short_stay' ou 'hotel'
    selected_province = request.GET.get('province', '').strip()
    search = request.GET.get('q', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    guests_str = request.GET.get('guests', '').strip()

    has_date_filter = bool(check_in_str and check_out_str)
    check_in_date, check_out_date = _parse_dates_with_defaults(check_in_str, check_out_str)

    try:
        guests_filter = max(1, int(guests_str)) if guests_str else None
    except ValueError:
        guests_filter = None

    db_items = Accommodation.objects.filter(is_active=True).prefetch_related('room_types')

    if db_items.exists():
        qs = db_items
        if selected_type:
            qs = qs.filter(accommodation_type=selected_type)
        elif selected_model == 'short_stay':
            qs = qs.filter(accommodation_type__in=['apartment', 'house', 'room', 'residence'])
        elif selected_model == 'hotel':
            qs = qs.filter(accommodation_type__in=['hotel', 'lodge', 'resort'])

        if selected_province:
            qs = qs.filter(province=selected_province)
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(city__icontains=search)
                | Q(description__icontains=search)
            )
        if max_price:
            try:
                qs = qs.filter(price_per_night_aoa__lte=float(max_price))
            except ValueError:
                pass

        accommodations = []
        for a in qs:
            avail_units = a.get_available_units_for_period(check_in_date, check_out_date)
            active_rts = [rt for rt in a.room_types.all() if rt.is_active]
            max_cap = max([a.max_guests] + [rt.capacity_guests for rt in active_rts])

            if guests_filter and max_cap < guests_filter:
                continue
            if has_date_filter and avail_units <= 0:
                continue

            accommodations.append({
                'id': a.pk,
                'name': a.name,
                'slug': a.slug,
                'accommodation_type': a.accommodation_type,
                'accommodation_type_label': a.get_accommodation_type_display(),
                'is_short_stay': a.accommodation_type in ('apartment', 'house', 'room', 'residence'),
                'room_types_count': len(active_rts),
                'available_units': avail_units,
                'province': a.province,
                'province_label': a.get_province_display(),
                'city': a.city,
                'short_description': a.short_description,
                'price_per_night_aoa': a.price_per_night_aoa,
                'formatted_price_aoa': a.formatted_price_aoa,
                'formatted_price_range_aoa': a.formatted_price_range_aoa,
                'price_per_night_usd': a.price_per_night_usd,
                'rating': a.rating,
                'review_count': a.review_count,
                'max_guests': max_cap,
                'bedrooms': a.bedrooms,
                'bathrooms': a.bathrooms,
                'amenities': a.amenities,
                'display_image': a.display_image,
                'is_featured': a.is_featured,
                'is_verified': a.is_verified,
                'verification_criteria': a.verification_criteria,
                'is_demo': a.is_demo,
            })
    else:
        accommodations = list(FALLBACK_ACCOMMODATIONS)

    context = {
        'page_title': 'Alojamento — Hotéis, Suites e Alojamentos de Curta Duração',
        'accommodations': accommodations,
        'total_count': len(accommodations),
        'selected_type': selected_type,
        'selected_model': selected_model,
        'selected_province': selected_province,
        'search_query': search,
        'max_price': max_price,
        'check_in': check_in_date.strftime('%Y-%m-%d') if has_date_filter else '',
        'check_out': check_out_date.strftime('%Y-%m-%d') if has_date_filter else '',
        'guests_filter': guests_filter or '',
        'types': Accommodation.TYPE_CHOICES,
        'provinces': Accommodation.PROVINCE_CHOICES,
        'is_filtered': bool(selected_type or selected_model or selected_province or search or max_price or has_date_filter or guests_filter),
    }
    return render(request, 'accommodations/list.html', context)


def accommodation_detail(request, slug):
    qs_all = Accommodation.objects.filter(slug=slug)
    if qs_all.exists():
        accommodation = get_object_or_404(
            Accommodation.objects.prefetch_related('room_types', 'gallery_photos'),
            slug=slug,
            is_active=True,
        )
    elif Accommodation.objects.filter(is_active=True).exists():
        raise Http404("Alojamento não encontrado.")
    else:
        match = next((x for x in FALLBACK_ACCOMMODATIONS if x['slug'] == slug), None)
        if not match:
            raise Http404("Alojamento não encontrado.")
        accommodation = match

    is_dict = isinstance(accommodation, dict)
    reviews = [] if is_dict else accommodation.reviews.all()[:10]

    check_in_str = request.GET.get('check_in', '').strip()
    check_out_str = request.GET.get('check_out', '').strip()
    check_in_date, check_out_date = _parse_dates_with_defaults(check_in_str, check_out_str)
    nights = max(1, (check_out_date - check_in_date).days)

    try:
        guests_selected = max(1, int(request.GET.get('guests', 2)))
    except ValueError:
        guests_selected = 2

    room_types_status = []
    acc_available_units = 1
    is_short_stay = False

    if not is_dict:
        is_short_stay = accommodation.accommodation_type in ('apartment', 'house', 'room', 'residence')
        acc_available_units = accommodation.get_available_units_for_period(check_in_date, check_out_date)
        for rt in accommodation.room_types.filter(is_active=True):
            avail = rt.get_available_units(check_in_date, check_out_date)
            period_total = float(rt.price_per_night_aoa) * nights
            room_types_status.append({
                'obj': rt,
                'id': rt.pk,
                'name': rt.name,
                'category_label': rt.get_category_display(),
                'description': rt.description,
                'capacity_guests': rt.capacity_guests,
                'beds_count': rt.beds_count,
                'bed_configuration': rt.bed_configuration,
                'amenities': rt.amenities or [],
                'price_per_night_aoa': rt.price_per_night_aoa,
                'formatted_price_aoa': rt.formatted_price_aoa,
                'period_total_aoa': f"{period_total:,.0f} Kz".replace(',', ' '),
                'total_units': rt.total_units,
                'available_units': avail,
                'is_available': avail > 0,
                'fits_guests': rt.capacity_guests >= guests_selected,
                'booking_conditions': rt.booking_conditions,
                'display_image': rt.display_image,
            })

    context = {
        'page_title': accommodation['name'] if is_dict else accommodation.name,
        'acc': accommodation,
        'is_dict': is_dict,
        'is_short_stay': is_short_stay,
        'reviews': reviews,
        'room_types_status': room_types_status,
        'acc_available_units': acc_available_units,
        'check_in': check_in_date.strftime('%Y-%m-%d'),
        'check_out': check_out_date.strftime('%Y-%m-%d'),
        'check_in_date': check_in_date,
        'check_out_date': check_out_date,
        'nights': nights,
        'guests_selected': guests_selected,
    }
    return render(request, 'accommodations/detail.html', context)


@require_POST
def accommodation_review(request, slug):
    """Avaliação verificada de alojamento: exige código de reserva concluída (Booking ou TripOrder)."""
    acc = get_object_or_404(Accommodation, slug=slug, is_active=True)
    booking_ref = request.POST.get('booking_reference', '').strip().upper()
    comment = request.POST.get('comment', '').strip()[:1000]
    try:
        rating = max(1, min(5, int(request.POST.get('rating', 5))))
    except (ValueError, TypeError):
        rating = 5

    if not booking_ref:
        messages.error(request, 'Indique o Código da Reserva Concluída (ex: DB-XXXXXX).')
        return redirect('accommodations:detail', slug=slug)

    guest_name = None
    direct_booking = Booking.objects.filter(
        accommodation=acc,
        reference_code__iexact=booking_ref,
        status='completed',
    ).first()

    if direct_booking:
        guest_name = direct_booking.guest_name
    else:
        trip_item = TripOrderItem.objects.select_related('order').filter(
            order__reference_code__iexact=booking_ref,
            item_type='accommodation',
            item_id=acc.pk,
        ).filter(
            Q(status='completed') | Q(order__status='completed')
        ).first()
        if trip_item:
            guest_name = trip_item.order.guest_name
            booking_ref = trip_item.order.reference_code

    if not guest_name:
        messages.error(
            request,
            f"O código '{booking_ref}' não corresponde a uma estadia concluída em {acc.name}. "
            "Só reservas com estado 'Concluída' podem avaliar."
        )
        return redirect('accommodations:detail', slug=slug)

    if AccommodationReview.objects.filter(accommodation=acc, booking_reference__iexact=booking_ref).exists():
        messages.info(request, f'A reserva #{booking_ref} já avaliou este alojamento.')
        return redirect('accommodations:detail', slug=slug)

    AccommodationReview.objects.create(
        accommodation=acc,
        booking_reference=booking_ref,
        guest_name=guest_name,
        rating=rating,
        comment=comment or 'Estadia concluída e verificada.',
    )

    agg = acc.reviews.aggregate(avg=Avg('rating'))
    acc.rating = round(agg['avg'] or 5.0, 1)
    acc.review_count = acc.reviews.count()
    acc.save(update_fields=['rating', 'review_count'])

    messages.success(request, f'Avaliação verificada da reserva #{booking_ref} registada com sucesso!')
    return redirect('accommodations:detail', slug=slug)


def _booking_rate_limited(request):
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    key = f'booking-rate:ip:{ip}'
    limit = getattr(settings, 'BOOKING_MAX_PER_IP', 5)
    timeout = getattr(settings, 'BOOKING_RATE_LIMIT_SECONDS', 900)
    current = cache.get(key) or 0
    if current >= limit:
        return True
    if not cache.add(key, 1, timeout):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout)
    return False


def accommodation_book(request, slug):
    if request.method != 'POST':
        return redirect('accommodations:detail', slug=slug)

    if _booking_rate_limited(request):
        messages.error(request, 'Demasiados pedidos de reserva em pouco tempo. Tente novamente mais tarde.')
        return HttpResponse(
            'Demasiados pedidos de reserva. Tente novamente mais tarde.',
            status=429,
            content_type='text/plain; charset=utf-8',
        )

    acc_instance = None
    fallback_match = None
    if Accommodation.objects.filter(slug=slug).exists():
        acc_instance = Accommodation.objects.filter(slug=slug, is_active=True).first()
        if acc_instance is None:
            messages.error(request, 'Este alojamento não se encontra activo para reservas.')
            return redirect('accommodations:list')
        max_allowed_guests = acc_instance.max_guests
    elif Accommodation.objects.filter(is_active=True).exists():
        raise Http404("Alojamento não encontrado.")
    else:
        fallback_match = next((x for x in FALLBACK_ACCOMMODATIONS if x['slug'] == slug), None)
        if not fallback_match:
            raise Http404("Alojamento não encontrado.")
        max_allowed_guests = fallback_match['max_guests']

    guest_name = request.POST.get('guest_name', '').strip()
    guest_email = request.POST.get('guest_email', '').strip()
    guest_phone = request.POST.get('guest_phone', '').strip()
    check_in_str = request.POST.get('check_in', '').strip()
    check_out_str = request.POST.get('check_out', '').strip()
    room_type_id = request.POST.get('room_type_id', '').strip()
    special_requests = request.POST.get('special_requests', '').strip()[:1000]

    try:
        units_reserved = max(1, min(10, int(request.POST.get('units_reserved', 1))))
    except (ValueError, TypeError):
        units_reserved = 1

    selected_room_type = None
    if acc_instance and room_type_id.isdigit():
        selected_room_type = RoomType.objects.filter(
            pk=int(room_type_id),
            accommodation=acc_instance,
            is_active=True,
        ).first()
        if selected_room_type:
            max_allowed_guests = max(max_allowed_guests, selected_room_type.capacity_guests * units_reserved)

    if not guest_name or len(guest_name) > 150:
        messages.error(request, 'Indique um nome válido (máx. 150 caracteres).')
        return redirect('accommodations:detail', slug=slug)

    try:
        validate_email(guest_email)
    except ValidationError:
        messages.error(request, 'Indique um endereço de email válido.')
        return redirect('accommodations:detail', slug=slug)

    if not PHONE_RE.match(guest_phone):
        messages.error(request, 'Indique um número de telefone válido.')
        return redirect('accommodations:detail', slug=slug)

    try:
        guests_count = int(request.POST.get('guests_count', 1))
    except (ValueError, TypeError):
        messages.error(request, 'Número de hóspedes inválido.')
        return redirect('accommodations:detail', slug=slug)

    if guests_count < 1 or guests_count > max_allowed_guests:
        messages.error(
            request,
            f'O número de hóspedes deve estar entre 1 e {max_allowed_guests}.',
        )
        return redirect('accommodations:detail', slug=slug)

    try:
        check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
        if check_in < datetime.date.today():
            messages.error(request, 'A data de entrada não pode estar no passado.')
            return redirect('accommodations:detail', slug=slug)
        if check_out <= check_in:
            messages.error(request, 'A data de saída tem de ser posterior à data de entrada.')
            return redirect('accommodations:detail', slug=slug)
        nights = (check_out - check_in).days
        if nights > 365:
            messages.error(request, 'A estadia não pode exceder 365 noites.')
            return redirect('accommodations:detail', slug=slug)
    except (ValueError, TypeError):
        messages.error(request, 'Datas inválidas fornecidas.')
        return redirect('accommodations:detail', slug=slug)

    # Validação de Disponibilidade e Inventário por Período (prevenção de sobre-reserva e conflito de datas)
    if acc_instance is not None:
        if selected_room_type is not None:
            avail_units = selected_room_type.get_available_units(check_in, check_out)
            if units_reserved > avail_units:
                messages.error(
                    request,
                    f"Indisponível: a tipologia '{selected_room_type.name}' tem apenas {avail_units} unidade(s) "
                    f"disponível(is) entre {check_in.strftime('%d/%m/%Y')} e {check_out.strftime('%d/%m/%Y')}.",
                )
                return redirect('accommodations:detail', slug=slug)
        else:
            avail_units = acc_instance.get_available_units_for_period(check_in, check_out)
            if units_reserved > avail_units:
                messages.error(
                    request,
                    f"Indisponível: '{acc_instance.name}' já se encontra reservado para o período "
                    f"de {check_in.strftime('%d/%m/%Y')} a {check_out.strftime('%d/%m/%Y')}.",
                )
                return redirect('accommodations:detail', slug=slug)

        booking = Booking.objects.create(
            accommodation=acc_instance,
            room_type=selected_room_type,
            units_reserved=units_reserved,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            check_in=check_in,
            check_out=check_out,
            guests_count=guests_count,
            special_requests=special_requests,
        )
        ref_code = booking.reference_code
        total_aoa = booking.total_price_aoa
        acc_name = f"{acc_instance.name} ({selected_room_type.name})" if selected_room_type else acc_instance.name
        whatsapp_phone = acc_instance.contact_whatsapp or '+244923111222'
    else:
        ref_code = f"DB-{datetime.datetime.now().strftime('%M%S')}"
        acc_name = fallback_match['name']
        total_aoa = nights * fallback_match['price_per_night_aoa']
        whatsapp_phone = fallback_match.get('contact_whatsapp', '+244923111222')

    msg_text = (
        f"Olá! Fiz um pedido de reserva no Destinos da Banda.\n"
        f"Alojamento: {acc_name}\n"
        f"Referência: {ref_code}\n"
        f"Nome: {guest_name}\n"
        f"Entrada: {check_in.strftime('%d/%m/%Y')} | Saída: {check_out.strftime('%d/%m/%Y')} ({nights} noites)\n"
        f"Hóspedes: {guests_count} | Unidades: {units_reserved}\n"
        f"Total Estimado: {total_aoa:,.0f} Kz"
    )
    clean_phone = re.sub(r'[^0-9]', '', whatsapp_phone)

    context = {
        'page_title': 'Confirmação da Pré-Reserva',
        'ref_code': ref_code,
        'guest_name': guest_name,
        'guest_email': guest_email,
        'guest_phone': guest_phone,
        'acc_name': acc_name,
        'room_type': selected_room_type,
        'units_reserved': units_reserved,
        'check_in': check_in,
        'check_out': check_out,
        'nights': nights,
        'guests_count': guests_count,
        'total_aoa': total_aoa,
        'whatsapp_url': f"https://wa.me/{clean_phone}?text={quote(msg_text)}",
    }
    messages.success(request, f'Pedido de reserva {ref_code} registado com sucesso!')
    return render(request, 'accommodations/booking_success.html', context)
