import datetime
import re
from urllib.parse import quote

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Event, EventBooking

PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,30}$')

FALLBACK_EVENTS = [
    {
        'id': 1,
        'title': 'Peregrinação & Romería Histórica da Nossa Senhora do Monte',
        'slug': 'romeria-nossa-senhora-do-monte-caala',
        'subtitle': 'O maior evento religioso, cultural e comunitário do Planalto Central, realizado anualmente a 15 de Agosto na Caála.',
        'activity_type': 'cultural',
        'activity_type_label': 'Evento Cultural & Festivo',
        'category': 'cultural',
        'category_label': 'Cultura, História & Património',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_venue': 'Santuário do Monte, Município da Caála, Huambo',
        'start_date': datetime.date(2026, 8, 13),
        'start_day': '13',
        'start_month': 'AGO',
        'end_date': datetime.date(2026, 8, 15),
        'time_schedule': '07:00 - 20:00',
        'duration': '3 Dias',
        'max_participants': 100,
        'available_spots': 100,
        'is_free': True,
        'price_aoa': 0,
        'formatted_price': '0 Kz (Gratuito)',
        'description': 'Um dos eventos mais emblemáticos da província do Huambo, reunindo milhares de visitantes no alto da colina da Caála.',
        'organizer_name': 'Arquidiocese do Huambo & Administração Municipal da Caála',
        'contact_phone': '+244 923 400 111',
        'contact_whatsapp': '+244923400111',
        'registration_link': '',
        'display_image': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1200&q=80',
        'is_featured': True,
        'is_verified': True,
        'verification_criteria': 'Evento oficial do calendário provincial do Huambo',
        'is_demo': False,
    },
]


def event_list(request):
    selected_type = request.GET.get('type', '')
    selected_category = request.GET.get('category', '')
    selected_province = request.GET.get('province', '')
    search = request.GET.get('q', '').strip()

    db_items = Event.objects.select_related('destination', 'guide').all()

    if db_items.exists():
        qs = db_items
        if selected_type:
            qs = qs.filter(activity_type=selected_type)
        if selected_category:
            qs = qs.filter(category=selected_category)
        if selected_province:
            qs = qs.filter(province=selected_province)
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(location_venue__icontains=search)
                | Q(description__icontains=search)
                | Q(itinerary__icontains=search)
            )

        events = []
        for e in qs:
            badge_key, badge_text = e.availability_badge
            events.append({
                'id': e.pk,
                'title': e.title,
                'slug': e.slug,
                'subtitle': e.subtitle,
                'activity_type': e.activity_type,
                'activity_type_label': e.get_activity_type_display(),
                'category': e.category,
                'category_label': e.get_category_display(),
                'province': e.province,
                'province_label': e.get_province_display(),
                'location_venue': e.location_venue,
                'start_date': e.start_date,
                'start_day': e.start_date.strftime('%d'),
                'start_month': e.start_date.strftime('%b').upper(),
                'end_date': e.end_date,
                'time_schedule': e.time_schedule,
                'duration': e.duration,
                'max_participants': e.max_participants,
                'available_spots': e.available_spots,
                'availability_key': badge_key,
                'availability_label': badge_text,
                'included_services': e.included_services or [],
                'destination': e.destination,
                'guide': e.guide,
                'is_free': e.is_free,
                'price_aoa': e.price_aoa,
                'formatted_price': e.formatted_price,
                'description': e.description,
                'organizer_name': e.organizer_name,
                'contact_phone': e.contact_phone,
                'contact_whatsapp': e.contact_whatsapp,
                'display_image': e.display_image,
                'is_featured': e.is_featured,
                'is_verified': e.is_verified,
                'verification_criteria': e.verification_criteria,
                'is_demo': e.is_demo,
            })
    else:
        events = list(FALLBACK_EVENTS)

    context = {
        'page_title': 'Tours, Experiências Turísticas e Eventos',
        'events': events,
        'total_count': len(events),
        'selected_type': selected_type,
        'selected_category': selected_category,
        'selected_province': selected_province,
        'search_query': search,
        'activity_types': Event.ACTIVITY_TYPE_CHOICES,
        'categories': Event.CATEGORY_CHOICES,
        'provinces': Event.PROVINCE_CHOICES,
        'is_filtered': bool(selected_type or selected_category or selected_province or search),
    }
    return render(request, 'events/list.html', context)


def event_detail(request, slug):
    event = Event.objects.select_related('destination', 'guide').filter(slug=slug).first()
    is_dict = False
    if not event:
        if Event.objects.exists():
            raise Http404("Tour ou Evento não encontrado.")
        event = next((x for x in FALLBACK_EVENTS if x['slug'] == slug), FALLBACK_EVENTS[0])
        is_dict = True

    title = event['title'] if is_dict else event.title
    venue = event['location_venue'] if is_dict else event.location_venue
    phone = (event['contact_whatsapp'] if is_dict else event.contact_whatsapp) or '+244923888777'
    wa_msg = f"Olá! Gostaria de reservar/participar na experiência '{title}' em {venue}."
    wa_url = f"https://wa.me/{phone.replace('+', '').replace(' ', '')}?text={quote(wa_msg)}"

    itinerary_lines = []
    included_services = []
    gallery_images = []
    related_articles = []
    has_map = False
    available_spots = 20
    badge_key, badge_label = ('available', 'Vagas disponíveis')

    if not is_dict:
        if event.itinerary:
            itinerary_lines = [line.strip() for line in event.itinerary.splitlines() if line.strip()]
        included_services = event.included_services or []
        gallery_images = event.gallery_images or []
        has_map = event.latitude is not None and event.longitude is not None
        available_spots = event.available_spots
        badge_key, badge_label = event.availability_badge
        related_articles = list(event.cultural_articles.filter(status='published')[:3])
        if not related_articles and event.destination:
            related_articles = list(event.destination.cultural_articles.filter(status='published')[:3])

    context = {
        'page_title': title,
        'event': event,
        'is_dict': is_dict,
        'whatsapp_url': wa_url,
        'itinerary_lines': itinerary_lines,
        'included_services': included_services,
        'gallery_images': gallery_images,
        'has_map': has_map,
        'available_spots': available_spots,
        'availability_key': badge_key,
        'availability_label': badge_label,
        'related_articles': related_articles,
    }
    return render(request, 'events/detail.html', context)


@require_POST
def event_book(request, slug):
    """Reserva ou inscrição direta numa Tour / Experiência Turística com validação real de vagas."""
    event = get_object_or_404(Event, slug=slug)

    if event.status == 'finished':
        messages.error(request, 'Esta experiência já se encontra encerrada.')
        return redirect('events:detail', slug=slug)

    participant_name = request.POST.get('participant_name', '').strip()
    participant_email = request.POST.get('participant_email', '').strip()
    participant_phone = request.POST.get('participant_phone', '').strip()
    selected_date_str = request.POST.get('selected_date', '').strip()
    special_notes = request.POST.get('special_notes', '').strip()[:1000]

    if not participant_name or len(participant_name) > 150:
        messages.error(request, 'Indique o seu nome completo.')
        return redirect('events:detail', slug=slug)

    try:
        validate_email(participant_email)
    except ValidationError:
        messages.error(request, 'Indique um endereço de email válido.')
        return redirect('events:detail', slug=slug)

    if not PHONE_RE.match(participant_phone):
        messages.error(request, 'Indique um número de telefone / WhatsApp válido.')
        return redirect('events:detail', slug=slug)

    try:
        participants_count = int(request.POST.get('participants_count', 1))
    except (ValueError, TypeError):
        messages.error(request, 'Número de participantes inválido.')
        return redirect('events:detail', slug=slug)

    if participants_count < 1:
        messages.error(request, 'O número de participantes deve ser pelo menos 1.')
        return redirect('events:detail', slug=slug)

    available = event.available_spots
    if participants_count > available:
        if available == 0:
            messages.error(request, 'Esta tour já atingiu o limite máximo de vagas.')
        else:
            messages.error(request, f'Restam apenas {available} vaga(s) disponíveis para esta experiência.')
        return redirect('events:detail', slug=slug)

    selected_date = event.start_date
    if selected_date_str:
        try:
            selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = event.start_date

    booking = EventBooking.objects.create(
        event=event,
        participant_name=participant_name,
        participant_email=participant_email,
        participant_phone=participant_phone,
        selected_date=selected_date,
        participants_count=participants_count,
        special_notes=special_notes,
        status='confirmed',
    )

    messages.success(
        request,
        f"Inscrição #{booking.reference_code} confirmada para '{event.title}' ({participants_count} participante(s))! "
        f"Vagas restantes: {event.available_spots}.",
    )
    return redirect('events:detail', slug=slug)
