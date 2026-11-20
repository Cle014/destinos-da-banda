
from django.shortcuts import render
from django.urls import reverse
from apps.destinations.models import Destination, Category
from apps.core.context_processors import get_province_wedge_status

def home_view(request):
    """
    View da página inicial — Fase 2.

    Os dados abaixo são estáticos e servem para construir
    o layout completo. Na Fase 3 virão da base de dados.
    A estrutura de cada dicionário já imita o futuro modelo Django.
    """

    hero_slides = [
        {
            'title': 'Morro do Moco',
            'subtitle': 'O ponto mais alto de Angola, no coração do Planalto Central.',
            'location': 'Londuimbali, Huambo',
            'image': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1600&q=80',
            'cta_text': 'Explorar Destino',
            'cta_url': '/destinos/morro-do-moco/',
        },
        {
            'title': 'Pedras de Nganda e Kawe',
            'subtitle': 'Monumentos graníticos milenares e paisagens místicas da Caála.',
            'location': 'Caála, Huambo',
            'image': 'https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1600&q=80',
            'cta_text': 'Descobrir Mais',
            'cta_url': '/destinos/pedras-nganda-kawe/',
        },
        {
            'title': 'Albufeira do Gove',
            'subtitle': 'Águas serenas sobre o rio Cunene, natureza e lazer no Planalto Central.',
            'location': 'Caála, Huambo',
            'image': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1600&q=80',
            'cta_text': 'Ver Huambo',
            'cta_url': '/destinos/albufeira-do-gove/',
        },
    ]

    categories = [
        {
            'name': 'Montanhas & Miradouros',
            'icon': 'fas fa-mountain',
            'color': '#2D6A4F',
            'count': 12,
            'slug': 'montanhas',
        },
        {
            'name': 'Parques & Reservas',
            'icon': 'fas fa-tree',
            'color': '#004D2A',
            'count': 8,
            'slug': 'parques-naturais',
        },
        {
            'name': 'História & Cultura',
            'icon': 'fas fa-landmark',
            'color': '#C8860A',
            'count': 15,
            'slug': 'historia-cultura',
        },
        {
            'name': 'Rios & Albufeiras',
            'icon': 'fas fa-water',
            'color': '#1A6B7A',
            'count': 10,
            'slug': 'rios-lagos',
        },
        {
            'name': 'Gastronomia',
            'icon': 'fas fa-utensils',
            'color': '#A06A00',
            'count': 18,
            'slug': 'gastronomia',
        },
        {
            'name': 'Aventura & Trilhos',
            'icon': 'fas fa-hiking',
            'color': '#5A3E28',
            'count': 14,
            'slug': 'aventura',
        },
    ]

    featured_destinations = [
        {
            'name': 'Morro do Moco',
            'province': 'Huambo',
            'category': 'Montanhas & Miradouros',
            'image': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
            'slug': 'morro-do-moco',
            'is_featured': True,
            'description': 'O cume mais elevado de Angola (2.620 m), santuário de floresta afromontana e aves endémicas em Londuimbali.',
        },
        {
            'name': 'Pedras de Nganda e Kawe (Pedras do Alemão)',
            'province': 'Huambo',
            'category': 'Montanhas & Miradouros',
            'image': 'https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=800&q=80',
            'slug': 'pedras-nganda-kawe',
            'is_featured': True,
            'description': 'Imponentes monólitos de granito na Caála, ideais para caminhadas e vistas panorâmicas sobre o Planalto Central.',
        },
        {
            'name': 'Albufeira e Barragem do Gove',
            'province': 'Huambo',
            'category': 'Rios & Quedas de Água',
            'image': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&q=80',
            'slug': 'albufeira-do-gove',
            'is_featured': True,
            'description': 'Vasto espelho de água no rio Cunene, perfeito para passeios náuticos, pesca desportiva e contemplação.',
        },
        {
            'name': 'Ombala Grande do Bailundo & Túmulo do Rei Ekuikui II',
            'province': 'Huambo',
            'category': 'História & Cultura',
            'image': 'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=800&q=80',
            'slug': 'ombala-bailundo',
            'is_featured': True,
            'description': 'Berço histórico e espiritual do Reino do Bailundo, guardião da tradição e memória Ovimbundu.',
        },
        {
            'name': 'Reserva Florestal do Kavongue (Parque da Chiva)',
            'province': 'Huambo',
            'category': 'Parques Naturais',
            'image': 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80',
            'slug': 'reserva-florestal-kavongue',
            'is_featured': True,
            'description': 'Pulmão verde às portas da cidade do Huambo, com trilhos arborizados, piqueniques e ar puro de altitude.',
        },
        {
            'name': 'Grutas de Soyo e Monte Sagrado de Leles',
            'province': 'Huambo',
            'category': 'Aventura & Safari',
            'image': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
            'slug': 'grutas-soyo-huambo',
            'is_featured': False,
            'description': 'Formações rochosas e cavernas históricas repletas de lendas ancestrais no interior da província.',
        },
    ]

    stats = [
        {'value': '11',   'label': 'Municípios', 'icon': 'fas fa-globe-africa'},
        {'value': '2620m','label': 'Morro do Moco', 'icon': 'fas fa-mountain'},
        {'value': '30+',  'label': 'Destinos no Huambo', 'icon': 'fas fa-map-marker-alt'},
        {'value': '100%', 'label': 'Planalto Central', 'icon': 'fas fa-users'},
    ]

    # Slides dinâmicos construídos a partir dos destinos reais publicados na base de dados
    slide_destinations_qs = (
        Destination.objects.filter(status='published')
        .select_related('category')
        .order_by('-is_featured', '-created_at')[:5]
    )
    dynamic_slides = []
    for d in slide_destinations_qs:
        if not d.display_image:
            continue
        location_parts = [p for p in (d.address, d.get_province_display()) if p]
        location_label = ', '.join(location_parts) if location_parts else d.get_province_display()
        dynamic_slides.append({
            'title': d.name,
            'subtitle': d.short_description or f'Descubra {d.name} em {d.get_province_display()}.',
            'location': location_label,
            'image': d.display_image,
            'cta_text': 'Explorar Destino',
            'cta_url': reverse('destinations:detail', kwargs={'slug': d.slug}),
        })

    if dynamic_slides:
        hero_slides = dynamic_slides

    featured_destinations_qs = Destination.objects.filter(
        status='published', is_featured=True
    ).select_related('category')[:6]

    categories_qs = Category.objects.all()[:8]

    featured_list = []
    for d in featured_destinations_qs:
        featured_list.append({
            'id': d.pk,
            'name': d.name,
            'province': d.get_province_display(),
            'category': d.category.name if d.category else '',
            'image': d.display_image,
            'slug': d.slug,
            'is_featured': d.is_featured,
            'is_verified': d.is_verified,
            'is_demo': d.is_demo,
            'price_range_aoa': d.formatted_fee_range_aoa,
            'description': d.short_description,
        })

    if not featured_list:
        featured_list = featured_destinations

    categories_list = []
    for c in categories_qs:
        categories_list.append({
            'name': c.name,
            'icon': c.icon,
            'color': c.color,
            'count': c.destination_count,
            'slug': c.slug,
        })

    if not categories_list:
        categories_list = categories

    context = {
        'page_title': 'Início',
        'hero_slides': hero_slides,
        'categories': categories_list,
        'featured_destinations': featured_list,
        'stats': stats,
        'provinces': Destination.PROVINCE_CHOICES,
    }
    return render(request, 'core/home.html', context)

def handler_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler_500(request):
    return render(request, 'errors/500.html', status=500)
