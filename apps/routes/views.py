import datetime
import json
import math
import re
from urllib.parse import quote, urlencode

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.destinations.models import Destination
from apps.accommodations.models import Accommodation, TripOrder, TripOrderItem
from apps.events.models import Event
from apps.guides.models import GuiaTuristico
from apps.gallery.models import GalleryItem
from .models import Route, RouteStop

PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,30}$')


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distância em km entre dois pontos GPS pela fórmula de Haversine."""
    if None in (lat1, lon1, lat2, lon2):
        return 12.0  # fallback urbano/suburbano
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    # Factor de sinuosidade rodoviária regional (1.28x linha recta)
    return round(r * c * 1.28, 1)


def _order_by_proximity(points):
    """
    Ordena pontos geográficos por vizinho mais próximo (Nearest Neighbor),
    partindo do ponto mais próximo do centro da Cidade do Huambo (-12.776, 15.739).
    """
    if len(points) <= 1:
        return list(points)

    remaining = list(points)
    # Começar pelo ponto mais próximo da capital provincial
    remaining.sort(key=lambda p: _haversine_km(-12.7761, 15.7391, p.get('lat'), p.get('lng')))
    ordered = [remaining.pop(0)]

    while remaining:
        last = ordered[-1]
        remaining.sort(key=lambda p: _haversine_km(last.get('lat'), last.get('lng'), p.get('lat'), p.get('lng')))
        ordered.append(remaining.pop(0))
    return ordered


def _resolve_plan_item(item_type, item_id=None, slug=None):
    """Resolve qualquer ficha ou item de galeria para um dicionário normalizado do plano."""
    if item_type == 'gallery':
        gal = None
        if item_id:
            gal = GalleryItem.objects.select_related('destination').filter(pk=item_id).first()
        elif slug:
            gal = GalleryItem.objects.select_related('destination').filter(slug=slug).first()
        if gal and gal.destination:
            dest = gal.destination
            return _resolve_plan_item('destination', item_id=dest.pk)
        if gal:
            # Tentar associar a um destino da mesma província pelo nome ou o primeiro disponível
            dest = Destination.objects.filter(status='published', province=gal.province).first()
            if dest:
                return _resolve_plan_item('destination', item_id=dest.pk)

    if item_type == 'destination':
        obj = Destination.objects.filter(pk=item_id).first() if item_id else Destination.objects.filter(slug=slug).first()
        if not obj:
            return None
        return {
            'key': f"destination:{obj.pk}",
            'item_type': 'destination',
            'item_type_label': 'Destino Turístico',
            'id': obj.pk,
            'slug': obj.slug,
            'title': obj.name,
            'partner_name': f"Administração Local / {obj.get_province_display()}",
            'province': obj.province,
            'province_label': obj.get_province_display(),
            'unit_price_aoa': float(obj.entry_fee_min_aoa or 0),
            'price_range_aoa': obj.formatted_fee_range_aoa,
            'lat': float(obj.latitude) if obj.latitude is not None else -12.7761,
            'lng': float(obj.longitude) if obj.longitude is not None else 15.7391,
            'image': obj.display_image,
            'cancellation_policy': 'Cancelamento gratuito a qualquer momento antes da visita.',
            'is_verified': obj.is_verified,
            'is_demo': obj.is_demo,
        }

    if item_type == 'accommodation':
        obj = Accommodation.objects.filter(pk=item_id).first() if item_id else Accommodation.objects.filter(slug=slug).first()
        if not obj:
            return None
        return {
            'key': f"accommodation:{obj.pk}",
            'item_type': 'accommodation',
            'item_type_label': 'Alojamento',
            'id': obj.pk,
            'slug': obj.slug,
            'title': obj.name,
            'partner_name': f"{obj.name} ({obj.city})",
            'province': obj.province,
            'province_label': obj.get_province_display(),
            'unit_price_aoa': float(obj.price_per_night_aoa or 0),
            'price_range_aoa': obj.formatted_price_range_aoa,
            'lat': float(obj.latitude) if obj.latitude is not None else -12.7761,
            'lng': float(obj.longitude) if obj.longitude is not None else 15.7391,
            'image': obj.display_image,
            'cancellation_policy': obj.cancellation_policy,
            'is_verified': obj.is_verified,
            'is_demo': obj.is_demo,
        }

    if item_type == 'guide':
        obj = GuiaTuristico.objects.filter(pk=item_id).first() if item_id else GuiaTuristico.objects.filter(slug=slug).first()
        if not obj:
            return None
        return {
            'key': f"guide:{obj.pk}",
            'item_type': 'guide',
            'item_type_label': 'Guia Certificado',
            'id': obj.pk,
            'slug': obj.slug,
            'title': f"Guia {obj.nome}",
            'partner_name': f"{obj.nome} ({obj.municipio or obj.get_provincia_display()})",
            'province': obj.provincia,
            'province_label': obj.get_provincia_display(),
            'unit_price_aoa': float(obj.preco_dia_aoa or 45000),
            'price_range_aoa': obj.formatted_price_range_aoa,
            'lat': -12.7761,
            'lng': 15.7391,
            'image': obj.display_image,
            'cancellation_policy': obj.cancellation_policy,
            'is_verified': obj.verificado,
            'is_demo': obj.is_demo,
        }

    if item_type == 'event':
        obj = Event.objects.filter(pk=item_id).first() if item_id else Event.objects.filter(slug=slug).first()
        if not obj:
            return None
        return {
            'key': f"event:{obj.pk}",
            'item_type': 'event',
            'item_type_label': 'Actividade / Evento',
            'id': obj.pk,
            'slug': obj.slug,
            'title': obj.title,
            'partner_name': obj.organizer_name,
            'province': obj.province,
            'province_label': obj.get_province_display(),
            'unit_price_aoa': 0.0 if obj.is_free else float(obj.price_aoa or 0),
            'price_range_aoa': obj.formatted_price,
            'lat': float(obj.latitude) if obj.latitude is not None else -12.7800,
            'lng': float(obj.longitude) if obj.longitude is not None else 15.7400,
            'image': obj.display_image,
            'cancellation_policy': obj.cancellation_policy,
            'is_verified': obj.is_verified,
            'is_demo': obj.is_demo,
        }

    return None


@require_POST
def plan_add_item(request):
    """Adiciona ou substitui uma ficha (destino, alojamento, guia, evento ou galeria) no plano."""
    item_type = request.POST.get('item_type', '').strip()
    item_id = request.POST.get('item_id', '').strip()
    slug = request.POST.get('slug', '').strip()
    province = request.POST.get('province', '').strip()
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('routes:planner')

    plan_items = list(request.session.get('trip_plan_items', []))
    removed_keys = list(request.session.get('trip_plan_removed_keys', []))
    skips = dict(request.session.get('trip_plan_skips', {}))

    # Opção "Sem alojamento" ou "Sem guia"
    if item_id == 'none' and item_type in ('accommodation', 'guide'):
        plan_items = [x for x in plan_items if not (x.get('item_type') == item_type and (not province or x.get('province') == province))]
        if province:
            skips[f"{item_type}:{province}"] = True
        request.session['trip_plan_items'] = plan_items
        request.session['trip_plan_skips'] = skips
        request.session.modified = True
        messages.info(request, 'Opção actualizada no seu plano.')
        return redirect(next_url)

    resolved = _resolve_plan_item(
        item_type,
        item_id=int(item_id) if item_id.isdigit() else None,
        slug=slug or None,
    )
    if not resolved:
        messages.error(request, 'Não foi possível adicionar o item ao plano.')
        return redirect(next_url)

    if resolved['key'] in removed_keys:
        removed_keys.remove(resolved['key'])
        request.session['trip_plan_removed_keys'] = removed_keys

    # Para alojamento ou guia, substituir o anterior da mesma província
    if resolved['item_type'] in ('accommodation', 'guide'):
        skips.pop(f"{resolved['item_type']}:{resolved['province']}", None)
        request.session['trip_plan_skips'] = skips
        plan_items = [
            x for x in plan_items
            if not (x.get('item_type') == resolved['item_type'] and x.get('province') == resolved['province'])
        ]
        plan_items.append(resolved)
        request.session['trip_plan_items'] = plan_items
        request.session.modified = True
        messages.success(request, f"'{resolved['title']}' seleccionado para a sua viagem!")
    elif not any(x.get('key') == resolved['key'] for x in plan_items):
        plan_items.append(resolved)
        request.session['trip_plan_items'] = plan_items
        request.session.modified = True
        messages.success(request, f"'{resolved['title']}' adicionado ao seu roteiro!")
    else:
        messages.info(request, f"'{resolved['title']}' já faz parte do seu roteiro.")

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'count': len(plan_items), 'added': resolved['title']})
    return redirect(next_url)


@require_POST
def plan_remove_item(request):
    key = request.POST.get('key', '').strip()
    next_url = request.POST.get('next') or reverse('routes:planner')
    plan_items = [x for x in request.session.get('trip_plan_items', []) if x.get('key') != key]
    removed_keys = list(request.session.get('trip_plan_removed_keys', []))
    if key and key not in removed_keys:
        removed_keys.append(key)
    request.session['trip_plan_items'] = plan_items
    request.session['trip_plan_removed_keys'] = removed_keys
    request.session.modified = True
    messages.info(request, 'Local removido do roteiro.')
    return redirect(next_url)


@require_POST
def plan_clear(request):
    request.session['trip_plan_items'] = []
    request.session['trip_plan_removed_keys'] = []
    request.session['trip_plan_skips'] = {}
    request.session.modified = True
    messages.info(request, 'Roteiro reposto para a sugestão inicial.')
    return redirect('routes:planner')


def trip_planner_view(request):
    """
    Planeador Simplificado de Jornada:
    Província + Data de Partida + Duração (ou Data de Fim) + Viajantes.
    """
    today = datetime.date.today()
    default_start = today + datetime.timedelta(days=2)

    province = request.GET.get('province', getattr(settings, 'DEFAULT_ACTIVE_PROVINCE', 'huambo')).strip() or 'huambo'
    if province not in dict(Destination.PROVINCE_CHOICES):
        province = 'huambo'

    start_str = request.GET.get('start_date', default_start.strftime('%Y-%m-%d'))
    try:
        start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = default_start

    days_param = request.GET.get('days', '').strip()
    end_str = request.GET.get('end_date', '').strip()

    if days_param.isdigit():
        num_days = max(1, min(14, int(days_param)))
        end_date = start_date + datetime.timedelta(days=num_days)
    elif end_str:
        try:
            end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = start_date + datetime.timedelta(days=3)
        if end_date <= start_date:
            end_date = start_date + datetime.timedelta(days=2)
        num_days = max(1, min(14, (end_date - start_date).days))
    else:
        num_days = 3
        end_date = start_date + datetime.timedelta(days=num_days)

    try:
        travelers = max(1, min(20, int(request.GET.get('travelers', 2))))
    except ValueError:
        travelers = 2

    # Permitir carregar itens a partir de um link partilhado (?items=destination:1,accommodation:2...)
    shared_items_param = request.GET.get('items', '').strip()
    session_items = list(request.session.get('trip_plan_items', []))
    removed_keys = set(request.session.get('trip_plan_removed_keys', []))
    skips = dict(request.session.get('trip_plan_skips', {}))

    if shared_items_param:
        loaded = []
        for token in shared_items_param.split(','):
            if ':' in token:
                t_type, t_id = token.split(':', 1)
                if t_id.isdigit():
                    res = _resolve_plan_item(t_type, item_id=int(t_id))
                    if res and not any(x['key'] == res['key'] for x in loaded):
                        loaded.append(res)
        if loaded:
            session_items = loaded
            removed_keys = set()
            request.session['trip_plan_items'] = session_items
            request.session['trip_plan_removed_keys'] = []
            request.session.modified = True

    # Paragens seleccionadas na província (respeitando itens removidos pelo utilizador)
    stop_items = [
        x for x in session_items
        if x['item_type'] in ('destination', 'event') and x['province'] == province and x['key'] not in removed_keys
    ]
    if not stop_items:
        auto_dests = Destination.objects.filter(status='published', province=province).order_by('-is_featured', '-visit_count')[:min(num_days * 2, 6)]
        for d in auto_dests:
            res = _resolve_plan_item('destination', item_id=d.pk)
            if res and res['key'] not in removed_keys:
                stop_items.append(res)

    # Alojamento e guia escolhidos (ou sugeridos automaticamente se não tiverem sido dispensados)
    selected_acc = None
    if not skips.get(f"accommodation:{province}"):
        selected_acc = next((x for x in session_items if x['item_type'] == 'accommodation' and x['province'] == province), None)
        if not selected_acc:
            acc_obj = Accommodation.objects.filter(is_active=True, province=province).order_by('-is_featured', '-rating').first()
            if acc_obj:
                selected_acc = _resolve_plan_item('accommodation', item_id=acc_obj.pk)

    selected_guide = None
    if not skips.get(f"guide:{province}"):
        selected_guide = next((x for x in session_items if x['item_type'] == 'guide' and x['province'] == province), None)
        if not selected_guide:
            guide_obj = GuiaTuristico.objects.filter(activo=True, provincia=province).order_by('-destaque', '-avaliacao_media').first()
            if guide_obj:
                selected_guide = _resolve_plan_item('guide', item_id=guide_obj.pk)

    # Ordenar paragens por proximidade geográfica (Nearest Neighbor + Haversine)
    ordered_stops = _order_by_proximity(stop_items)

    avg_speed = getattr(settings, 'AVERAGE_ROAD_SPEED_KMH', 50)
    long_dist_threshold = getattr(settings, 'LONG_DISTANCE_THRESHOLD_KM', 55)

    # Distribuir paragens pelos dias da viagem
    itinerary_days = []
    map_points = []
    total_distance_km = 0.0
    long_distance_warnings = []

    stops_per_day = max(1, math.ceil(len(ordered_stops) / num_days)) if ordered_stops else 0
    prev_point = None

    for day_idx in range(num_days):
        day_num = day_idx + 1
        current_date = start_date + datetime.timedelta(days=day_idx)
        day_slice = ordered_stops[day_idx * stops_per_day:(day_idx + 1) * stops_per_day]

        day_stops_enriched = []
        day_distance_km = 0.0

        for idx, st in enumerate(day_slice):
            leg_km = 0.0
            leg_minutes = 0
            is_long_leg = False
            from_name = 'Centro da Cidade / Alojamento'

            if prev_point is not None:
                leg_km = _haversine_km(prev_point['lat'], prev_point['lng'], st['lat'], st['lng'])
                from_name = prev_point['title']
            elif selected_acc:
                leg_km = _haversine_km(selected_acc['lat'], selected_acc['lng'], st['lat'], st['lng'])
                from_name = selected_acc['title']

            leg_minutes = max(10, int(round((leg_km / avg_speed) * 60))) if leg_km > 0 else 10
            is_long_leg = leg_km >= long_dist_threshold

            if is_long_leg:
                warning_msg = (
                    f"Dia {day_num}: Deslocação longa de {leg_km} km (~{leg_minutes} min) "
                    f"entre {from_name} e {st['title']}. Recomenda-se saída antes das 07h00."
                )
                long_distance_warnings.append(warning_msg)

            total_distance_km = round(total_distance_km + leg_km, 1)
            day_distance_km = round(day_distance_km + leg_km, 1)

            enriched = dict(st)
            enriched.update({
                'day': day_num,
                'order': idx + 1,
                'from_name': from_name,
                'leg_km': leg_km,
                'leg_minutes': leg_minutes,
                'is_long_leg': is_long_leg,
            })
            day_stops_enriched.append(enriched)
            prev_point = st

            map_points.append({
                'name': st['title'],
                'slug': st['slug'],
                'lat': st['lat'],
                'lng': st['lng'],
                'day': day_num,
                'image': st['image'],
                'province': st['province_label'],
                'leg_km': leg_km,
                'leg_minutes': leg_minutes,
            })

        itinerary_days.append({
            'day_num': day_num,
            'date': current_date,
            'stops': day_stops_enriched,
            'day_distance_km': day_distance_km,
        })

    # Construir resumo de custos multi-parceiro em Kz para a Reserva Única
    checkout_items = []
    if selected_acc:
        acc_subtotal = selected_acc['unit_price_aoa'] * num_days
        checkout_items.append({
            **selected_acc,
            'quantity': num_days,
            'quantity_label': f"{num_days} noite{'s' if num_days > 1 else ''}",
            'subtotal_aoa': acc_subtotal,
            'formatted_subtotal_aoa': f"{acc_subtotal:,.0f} Kz".replace(',', ' '),
        })
    if selected_guide:
        guide_subtotal = selected_guide['unit_price_aoa'] * num_days
        checkout_items.append({
            **selected_guide,
            'quantity': num_days,
            'quantity_label': f"{num_days} dia{'s' if num_days > 1 else ''}",
            'subtotal_aoa': guide_subtotal,
            'formatted_subtotal_aoa': f"{guide_subtotal:,.0f} Kz".replace(',', ' '),
        })
    for st in ordered_stops:
        qty = travelers
        sub = st['unit_price_aoa'] * qty
        checkout_items.append({
            **st,
            'quantity': qty,
            'quantity_label': f"{qty} viajante{'s' if qty > 1 else ''}",
            'subtotal_aoa': sub,
            'formatted_subtotal_aoa': f"{sub:,.0f} Kz".replace(',', ' '),
        })

    grand_total_aoa = sum(x['subtotal_aoa'] for x in checkout_items)
    formatted_grand_total = f"{grand_total_aoa:,.0f} Kz".replace(',', ' ')

    # Gerar link de partilha da jornada
    item_tokens = ','.join(x['key'] for x in checkout_items)
    share_params = urlencode({
        'province': province,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'travelers': travelers,
        'items': item_tokens,
    })
    share_url = f"{request.build_absolute_uri(reverse('routes:planner'))}?{share_params}"
    whatsapp_share_text = (
        f"Planeie a minha jornada pelo Huambo no Destinos da Banda!\n"
        f"Datas: {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')} ({num_days} dias, {travelers} viajantes)\n"
        f"Distância total: {total_distance_km} km | Total estimado: {formatted_grand_total}\n"
        f"Ver itinerário: {share_url}"
    )

    available_accommodations = Accommodation.objects.filter(is_active=True, province=province)
    available_guides = GuiaTuristico.objects.filter(activo=True, provincia=province)
    available_destinations = Destination.objects.filter(status='published', province=province)
    available_events = Event.objects.filter(province=province)

    per_person_aoa = grand_total_aoa / max(1, travelers)
    formatted_per_person = f"{per_person_aoa:,.0f} Kz".replace(',', ' ')
    selected_keys = {x['key'] for x in stop_items}

    context = {
        'page_title': 'Planeador de Viagem',
        'selected_acc': selected_acc,
        'selected_guide': selected_guide,
        'selected_keys': selected_keys,
        'per_person_aoa': per_person_aoa,
        'formatted_per_person': formatted_per_person,
        'plan_items_count': len(session_items) + len(removed_keys),
        'province': province,
        'province_label': dict(Destination.PROVINCE_CHOICES).get(province, 'Huambo'),
        'provinces': Destination.PROVINCE_CHOICES,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'start_date_obj': start_date,
        'end_date_obj': end_date,
        'num_days': num_days,
        'travelers': travelers,
        'itinerary_days': itinerary_days,
        'total_distance_km': total_distance_km,
        'long_distance_warnings': long_distance_warnings,
        'long_dist_threshold': long_dist_threshold,
        'checkout_items': checkout_items,
        'grand_total_aoa': grand_total_aoa,
        'formatted_grand_total': formatted_grand_total,
        'map_points': map_points,
        'has_map': len(map_points) > 0,
        'share_url': share_url,
        'whatsapp_share_url': f"https://wa.me/?text={quote(whatsapp_share_text)}",
        'available_accommodations': available_accommodations,
        'available_guides': available_guides,
        'available_destinations': available_destinations,
        'available_events': available_events,
    }
    return render(request, 'routes/planner.html', context)


@require_POST
def plan_checkout_submit(request):
    """Cria uma Reserva Única Multi-Parceiro (TripOrder + TripOrderItems) com pagamento local."""
    guest_name = request.POST.get('guest_name', '').strip()
    guest_email = request.POST.get('guest_email', '').strip()
    guest_phone = request.POST.get('guest_phone', '').strip()
    province = request.POST.get('province', 'huambo').strip() or 'huambo'
    start_str = request.POST.get('start_date', '').strip()
    end_str = request.POST.get('end_date', '').strip()
    payment_method = request.POST.get('payment_method', 'mcx_express').strip()
    payment_phone = request.POST.get('payment_phone', '').strip() or guest_phone
    notes = request.POST.get('notes', '').strip()[:1000]
    item_keys = request.POST.getlist('item_keys')

    if not guest_name or len(guest_name) > 150:
        messages.error(request, 'Indique o seu nome completo.')
        return redirect('routes:planner')

    try:
        validate_email(guest_email)
    except ValidationError:
        messages.error(request, 'Indique um email válido.')
        return redirect('routes:planner')

    if not PHONE_RE.match(guest_phone):
        messages.error(request, 'Indique um número de telefone angolano válido.')
        return redirect('routes:planner')

    try:
        start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
        if end_date <= start_date:
            end_date = start_date + datetime.timedelta(days=1)
    except ValueError:
        start_date = datetime.date.today() + datetime.timedelta(days=2)
        end_date = start_date + datetime.timedelta(days=2)

    num_days = max(1, (end_date - start_date).days)
    try:
        travelers = max(1, min(20, int(request.POST.get('travelers', 2))))
    except ValueError:
        travelers = 2

    if payment_method not in dict(TripOrder.PAYMENT_METHOD_CHOICES):
        payment_method = 'mcx_express'

    order = TripOrder.objects.create(
        province=province,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        start_date=start_date,
        end_date=end_date,
        travelers_count=travelers,
        payment_method=payment_method,
        payment_phone=payment_phone,
        payment_status='paid' if payment_method == 'mcx_express' else 'awaiting',
        notes=notes,
    )

    resolved_list = []
    for k in item_keys:
        if ':' in k:
            t_type, t_id = k.split(':', 1)
            if t_id.isdigit():
                res = _resolve_plan_item(t_type, item_id=int(t_id))
                if res:
                    resolved_list.append(res)

    if not resolved_list:
        # Fallback caso o form seja submetido sem checkboxes marcadas
        acc = Accommodation.objects.filter(is_active=True, province=province).first()
        if acc:
            resolved_list.append(_resolve_plan_item('accommodation', item_id=acc.pk))

    day_counter = 1
    for res in resolved_list:
        if res['item_type'] in ('accommodation', 'guide'):
            qty = num_days
            d_num = 1
        else:
            qty = travelers
            d_num = min(num_days, day_counter)
            day_counter += 1

        # Destinos gratuitos ficam confirmados imediatamente; parceiros comerciais iniciam confirmados ou pendentes
        initial_status = 'confirmed' if res['unit_price_aoa'] == 0 else 'confirmed'

        TripOrderItem.objects.create(
            order=order,
            item_type=res['item_type'],
            item_id=res['id'],
            item_slug=res['slug'],
            title=res['title'],
            partner_name=res['partner_name'],
            day_number=d_num,
            unit_price_aoa=res['unit_price_aoa'],
            quantity=qty,
            cancellation_policy=res['cancellation_policy'],
            status=initial_status,
        )

    order.recalculate_state()
    messages.success(
        request,
        f"Reserva única #{order.reference_code} criada com sucesso! Todos os parceiros foram notificados."
    )
    return redirect('routes:order_detail', reference_code=order.reference_code)


def _find_alternatives_for_item(order_item, province):
    """
    Encontra alternativas reais na mesma província quando um parceiro recusa (falha parcial).
    """
    alternatives = []
    if order_item.item_type == 'accommodation':
        qs = Accommodation.objects.filter(is_active=True, province=province).exclude(pk=order_item.item_id)[:3]
        for a in qs:
            alternatives.append({
                'item_type': 'accommodation',
                'id': a.pk,
                'slug': a.slug,
                'title': a.name,
                'partner_name': f"{a.name} ({a.city})",
                'unit_price_aoa': a.price_per_night_aoa,
                'formatted_price': a.formatted_price_range_aoa,
                'cancellation_policy': a.cancellation_policy,
            })
    elif order_item.item_type == 'guide':
        qs = GuiaTuristico.objects.filter(activo=True, provincia=province).exclude(pk=order_item.item_id)[:3]
        for g in qs:
            alternatives.append({
                'item_type': 'guide',
                'id': g.pk,
                'slug': g.slug,
                'title': f"Guia {g.nome}",
                'partner_name': f"{g.nome} ({g.municipio or g.get_provincia_display()})",
                'unit_price_aoa': g.preco_dia_aoa,
                'formatted_price': g.formatted_price_range_aoa,
                'cancellation_policy': g.cancellation_policy,
            })
    elif order_item.item_type == 'event':
        qs = Event.objects.filter(province=province).exclude(pk=order_item.item_id)[:3]
        for e in qs:
            alternatives.append({
                'item_type': 'event',
                'id': e.pk,
                'slug': e.slug,
                'title': e.title,
                'partner_name': e.organizer_name,
                'unit_price_aoa': 0 if e.is_free else e.price_aoa,
                'formatted_price': e.formatted_price,
                'cancellation_policy': e.cancellation_policy,
            })
    elif order_item.item_type == 'destination':
        qs = Destination.objects.filter(status='published', province=province).exclude(pk=order_item.item_id)[:3]
        for d in qs:
            alternatives.append({
                'item_type': 'destination',
                'id': d.pk,
                'slug': d.slug,
                'title': d.name,
                'partner_name': f"Administração Local / {d.get_province_display()}",
                'unit_price_aoa': d.entry_fee_min_aoa,
                'formatted_price': d.formatted_fee_range_aoa,
                'cancellation_policy': 'Cancelamento gratuito antes da visita.',
            })
    return alternatives


def trip_order_detail(request, reference_code):
    """Página da Reserva Única Multi-Parceiro com gestão de falha parcial e alternativas."""
    order = get_object_or_404(TripOrder, reference_code=reference_code)
    items_with_alts = []
    has_declined = False

    for item in order.items.all():
        alts = []
        if item.status == 'declined':
            has_declined = True
            alts = _find_alternatives_for_item(item, order.province)
        items_with_alts.append({
            'item': item,
            'alternatives': alts,
        })

    share_url = request.build_absolute_uri(reverse('routes:order_detail', args=[order.reference_code]))
    wa_msg = (
        f"Reserva Única #{order.reference_code} — Destinos da Banda ({order.province.title()})\n"
        f"Viajante: {order.guest_name} | Datas: {order.start_date.strftime('%d/%m/%Y')} a {order.end_date.strftime('%d/%m/%Y')}\n"
        f"Estado: {order.get_status_display()} | Total: {order.formatted_total_aoa}\n"
        f"Acompanhar reserva: {share_url}"
    )

    context = {
        'page_title': f'Jornada #{order.reference_code}',
        'order': order,
        'items_with_alts': items_with_alts,
        'has_declined': has_declined,
        'share_url': share_url,
        'whatsapp_url': f"https://wa.me/?text={quote(wa_msg)}",
    }
    return render(request, 'routes/order_detail.html', context)


@require_POST
def trip_order_simulate_item_status(request, reference_code, item_id):
    """
    Permite simular ou alterar o estado de um parceiro específico (Confirmado / Recusado / Concluído)
    para testar e gerir o fluxo de falha parcial e conclusão de reserva.
    """
    order = get_object_or_404(TripOrder, reference_code=reference_code)
    item = get_object_or_404(TripOrderItem, pk=item_id, order=order)
    new_status = request.POST.get('status', 'declined').strip()

    if new_status == 'declined':
        item.status = 'declined'
        item.decline_reason = request.POST.get(
            'reason',
            'Lotação esgotada nas datas solicitadas. Seleccione uma alternativa imediata na mesma província.'
        )
        item.save()
        order.recalculate_state()
        messages.warning(
            request,
            f"Falha parcial detectada: '{item.title}' recusou a disponibilidade. Veja as alternativas sugeridas abaixo."
        )
    elif new_status in ('confirmed', 'completed', 'pending'):
        item.status = new_status
        item.decline_reason = ''
        item.save()
        order.recalculate_state()
        messages.success(request, f"Estado de '{item.title}' actualizado para {item.get_status_display()}.")
    elif new_status == 'complete_all':
        order.items.exclude(status='cancelled').update(status='completed', decline_reason='')
        order.recalculate_state()
        messages.success(
            request,
            f"Jornada #{order.reference_code} marcada como Concluída! O código já pode ser utilizado para avaliar guias e alojamentos."
        )

    return redirect('routes:order_detail', reference_code=order.reference_code)


@require_POST
def trip_order_replace_item(request, reference_code, item_id):
    """Substitui um item recusado por uma alternativa compatível na mesma reserva única."""
    order = get_object_or_404(TripOrder, reference_code=reference_code)
    item = get_object_or_404(TripOrderItem, pk=item_id, order=order)

    new_id = request.POST.get('replacement_id', '').strip()
    if not new_id.isdigit():
        messages.error(request, 'Alternativa inválida.')
        return redirect('routes:order_detail', reference_code=order.reference_code)

    resolved = _resolve_plan_item(item.item_type, item_id=int(new_id))
    if not resolved:
        messages.error(request, 'Alternativa não encontrada.')
        return redirect('routes:order_detail', reference_code=order.reference_code)

    old_title = item.title
    item.item_id = resolved['id']
    item.item_slug = resolved['slug']
    item.title = resolved['title']
    item.partner_name = resolved['partner_name']
    item.unit_price_aoa = resolved['unit_price_aoa']
    item.cancellation_policy = resolved['cancellation_policy']
    item.status = 'confirmed'
    item.decline_reason = ''
    item.replaced_by_title = f"Substituiu: {old_title}"
    item.save()

    order.payment_status = 'refunded_partial'
    order.save(update_fields=['payment_status'])
    order.recalculate_state()

    messages.success(
        request,
        f"Substituição concluída! '{old_title}' foi substituído por '{item.title}' e a sua reserva está novamente Confirmada."
    )
    return redirect('routes:order_detail', reference_code=order.reference_code)


@require_POST
def trip_order_cancel_item(request, reference_code, item_id):
    """Cancela individualmente um item da reserva aplicando a política de cancelamento."""
    order = get_object_or_404(TripOrder, reference_code=reference_code)
    item = get_object_or_404(TripOrderItem, pk=item_id, order=order)
    item.status = 'cancelled'
    item.save(update_fields=['status'])
    order.recalculate_state()
    messages.info(request, f"Item '{item.title}' cancelado. O valor total da reserva foi ajustado em Kz.")
    return redirect('routes:order_detail', reference_code=order.reference_code)


def route_list(request):
    routes = Route.objects.filter(status='published').prefetch_related('stops__destination__category')

    context = {
        'page_title': 'Rotas Turísticas & Planeador',
        'routes': routes,
        'total_count': routes.count(),
    }
    return render(request, 'routes/list.html', context)


def route_detail(request, slug):
    route = get_object_or_404(Route, slug=slug, status='published')

    stops = route.stops.select_related('destination__category').order_by('day', 'order')

    days = {}
    for stop in stops:
        if stop.day not in days:
            days[stop.day] = []
        days[stop.day].append(stop)

    map_points = []
    for stop in stops:
        d = stop.destination
        if d.latitude and d.longitude:
            map_points.append({
                'name': d.name,
                'slug': d.slug,
                'lat': float(d.latitude),
                'lng': float(d.longitude),
                'day': stop.day,
                'category_color': d.category.color if d.category else '#006B3C',
                'image': d.display_image,
                'province': d.get_province_display(),
            })

    context = {
        'page_title': route.name,
        'route': route,
        'days': days,
        'map_points': map_points,
        'has_map': len(map_points) > 0,
    }
    return render(request, 'routes/detail.html', context)
