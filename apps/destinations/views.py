import datetime
import re
from urllib.parse import quote

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.db.models import F, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Destination, Category, DestinationVisitBooking, CulturalArticle
from .filters import DestinationFilter

PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,30}$')


def destination_list(request):
    """
    Listagem de Destinos e Visitas (incluindo Agroturismo integrado nas Categorias)
    e destaque editorial do Blog Cultural.
    """
    queryset = Destination.objects.filter(
        status='published'
    ).select_related('category')

    destination_filter = DestinationFilter(request.GET, queryset=queryset)
    filtered_qs = destination_filter.qs

    paginator = Paginator(filtered_qs, 12)
    page_number = request.GET.get('page', 1)

    try:
        destinations = paginator.page(page_number)
    except PageNotAnInteger:
        destinations = paginator.page(1)
    except EmptyPage:
        destinations = paginator.page(paginator.num_pages)

    categories = Category.objects.all()
    provinces = Destination.PROVINCE_CHOICES
    total_count = filtered_qs.count()
    featured_articles = CulturalArticle.objects.filter(status='published').select_related('destination', 'related_tour')[:3]

    context = {
        'page_title': 'Destinos, Visitas & Agroturismo',
        'destinations': destinations,
        'filter': destination_filter,
        'categories': categories,
        'provinces': provinces,
        'total_count': total_count,
        'is_filtered': bool(request.GET),
        'selected_category': request.GET.get('category', ''),
        'featured_articles': featured_articles,
    }
    return render(request, 'destinations/list.html', context)


def destination_detail(request, slug):
    """
    Página de detalhe de um Destino / Visita / Experiência de Agroturismo.
    Inclui actividades disponíveis, duração, capacidade, anfitrião, reserva de visita,
    tours disponíveis no destino e histórias do Blog Cultural.
    """
    destination = get_object_or_404(
        Destination.objects.select_related('category'),
        slug=slug,
        status='published',
    )

    destination.increment_visits()
    gallery = destination.gallery.all()

    related = Destination.objects.filter(
        status='published',
        category=destination.category,
    ).exclude(pk=destination.pk).select_related('category')[:3]

    related_tours = destination.tours_and_events.exclude(status='finished')[:4]
    related_articles = destination.cultural_articles.filter(status='published')[:4]

    visit_date_str = request.GET.get('visit_date', (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d'))
    try:
        visit_date = datetime.datetime.strptime(visit_date_str, '%Y-%m-%d').date()
    except ValueError:
        visit_date = datetime.date.today() + datetime.timedelta(days=2)

    available_spots = destination.get_available_visit_spots(visit_date)
    phone = destination.contact_whatsapp or destination.contact_phone or '+244923410100'
    wa_msg = f"Olá! Gostaria de agendar uma visita a '{destination.name}' ({destination.get_province_display()})."
    wa_url = f"https://wa.me/{phone.replace('+', '').replace(' ', '')}?text={quote(wa_msg)}"

    context = {
        'page_title': destination.name,
        'destination': destination,
        'gallery': gallery,
        'related': related,
        'related_tours': related_tours,
        'related_articles': related_articles,
        'has_map': destination.has_coordinates,
        'visit_date': visit_date.strftime('%Y-%m-%d'),
        'available_spots': available_spots,
        'whatsapp_url': wa_url,
        'is_agroturismo': bool(destination.category and destination.category.slug == 'agroturismo'),
    }
    return render(request, 'destinations/detail.html', context)


@require_POST
def destination_visit_book(request, slug):
    """Reserva de Visita ou Experiência de Agroturismo com verificação real de capacidade."""
    destination = get_object_or_404(Destination, slug=slug, status='published')

    visitor_name = request.POST.get('visitor_name', '').strip()
    visitor_email = request.POST.get('visitor_email', '').strip()
    visitor_phone = request.POST.get('visitor_phone', '').strip()
    visit_date_str = request.POST.get('visit_date', '').strip()
    notes = request.POST.get('notes', '').strip()[:1000]

    if not visitor_name or len(visitor_name) > 150:
        messages.error(request, 'Indique o seu nome completo.')
        return redirect('destinations:detail', slug=slug)

    try:
        validate_email(visitor_email)
    except ValidationError:
        messages.error(request, 'Indique um endereço de email válido.')
        return redirect('destinations:detail', slug=slug)

    if not PHONE_RE.match(visitor_phone):
        messages.error(request, 'Indique um número de telefone / WhatsApp válido.')
        return redirect('destinations:detail', slug=slug)

    try:
        participants_count = int(
            request.POST.get('participants_count')
            or request.POST.get('visitors_count')
            or 1
        )
    except (ValueError, TypeError):
        messages.error(request, 'Número de participantes inválido.')
        return redirect('destinations:detail', slug=slug)

    if participants_count < 1:
        messages.error(request, 'O número de participantes deve ser pelo menos 1.')
        return redirect('destinations:detail', slug=slug)

    try:
        visit_date = datetime.datetime.strptime(visit_date_str, '%Y-%m-%d').date()
        if visit_date < datetime.date.today():
            messages.error(request, 'A data da visita não pode estar no passado.')
            return redirect('destinations:detail', slug=slug)
    except ValueError:
        visit_date = datetime.date.today() + datetime.timedelta(days=2)

    available = destination.get_available_visit_spots(visit_date)
    if participants_count > available:
        messages.error(
            request,
            f'Para a data {visit_date.strftime("%d/%m/%Y")}, restam apenas {available} vaga(s) em {destination.name}.',
        )
        return redirect('destinations:detail', slug=slug)

    booking = DestinationVisitBooking.objects.create(
        destination=destination,
        visitor_name=visitor_name,
        visitor_email=visitor_email,
        visitor_phone=visitor_phone,
        visit_date=visit_date,
        participants_count=participants_count,
        notes=notes,
        status='confirmed',
    )

    messages.success(
        request,
        f"Visita #{booking.reference_code} agendada para {visit_date.strftime('%d/%m/%Y')} "
        f"({participants_count} participante(s)) com {destination.host_name or destination.name}!",
    )
    return redirect('destinations:detail', slug=slug)


# ---------------------------------------------------------------------------
# BLOG CULTURAL — HISTÓRIAS, CULTURA E DESTINOS
# ---------------------------------------------------------------------------

def article_list(request):
    topic = request.GET.get('topic', '').strip()
    province = request.GET.get('province', '').strip()
    tag = request.GET.get('tag', '').strip()
    search = request.GET.get('q', '').strip()

    qs = CulturalArticle.objects.filter(status='published').select_related('destination', 'related_tour')
    if topic:
        qs = qs.filter(topic=topic)
    if province:
        qs = qs.filter(province=province)
    if tag:
        qs = qs.filter(tags__icontains=tag)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(subtitle__icontains=search)
            | Q(summary__icontains=search)
            | Q(content__icontains=search)
            | Q(location_name__icontains=search)
        )

    context = {
        'page_title': 'Blog Cultural — Histórias, Cultura e Destinos',
        'articles': qs,
        'total_count': qs.count(),
        'topics': CulturalArticle.TOPIC_CHOICES,
        'provinces': Destination.PROVINCE_CHOICES,
        'selected_topic': topic,
        'selected_province': province,
        'selected_tag': tag,
        'search_query': search,
        'is_filtered': bool(topic or province or tag or search),
    }
    return render(request, 'destinations/article_list.html', context)


def article_detail(request, slug):
    article = get_object_or_404(
        CulturalArticle.objects.select_related('destination', 'related_tour'),
        slug=slug,
        status='published',
    )
    CulturalArticle.objects.filter(pk=article.pk).update(view_count=F('view_count') + 1)

    related_articles = CulturalArticle.objects.filter(
        status='published',
    ).exclude(pk=article.pk).select_related('destination')[:3]

    destination_tours = []
    if article.destination:
        destination_tours = list(article.destination.tours_and_events.exclude(status='finished')[:3])

    context = {
        'page_title': article.title,
        'article': article,
        'related_articles': related_articles,
        'destination_tours': destination_tours,
    }
    return render(request, 'destinations/article_detail.html', context)
