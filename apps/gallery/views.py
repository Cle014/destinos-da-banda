from django.shortcuts import render
from .models import GalleryItem

FALLBACK_GALLERY_ITEMS = [
    {
        'title': 'Amanhecer no Cume do Morro do Moco (2.620 m)',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'natureza',
        'category_label': 'Natureza & Vida Selvagem',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Londuimbali, Huambo',
        'description': 'O ponto mais alto de Angola envolto na bruma matinal do Planalto Central, refúgio de aves endémicas e ravinas de floresta afromontana.',
        'display_image': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1200&q=80',
        'photographer': 'Destinos da Banda Huambo',
        'activity_date': 'Outubro 2026',
        'is_featured': True,
    },
    {
        'title': 'Monólitos Graníticos das Pedras de Nganda e Kawe',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'natureza',
        'category_label': 'Natureza & Vida Selvagem',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Caála, Huambo',
        'description': 'Conhecidas como Pedras do Alemão, estas formações rochosas colossais erguem-se sobre a savana da Caála com vistas de 360 graus.',
        'display_image': 'https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1200&q=80',
        'photographer': 'Turismo Planalto Central',
        'activity_date': 'Setembro 2026',
        'is_featured': True,
    },
    {
        'title': 'Espelho de Água da Albufeira do Gove',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'natureza',
        'category_label': 'Natureza & Vida Selvagem',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Barragem do Gove, Caála — Huambo',
        'description': 'As águas serenas represadas no rio Cunene formam uma paisagem deslumbrante de penínsulas e ilhotas verdes no sul da província.',
        'display_image': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200&q=80',
        'photographer': 'Clube Náutico do Gove',
        'activity_date': 'Agosto 2026',
        'is_featured': True,
    },
    {
        'title': 'Trekking e Montanhismo na Serra do Moco',
        'item_type': 'activity',
        'item_type_label': 'Actividade Turística / Recreativa',
        'category': 'aventura',
        'category_label': 'Aventura & Desporto',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Aldeia de Kanjonde, Londuimbali',
        'description': 'Subida pedestre pelos trilhos rochosos e cascatas cristalinas do Morro do Moco acompanhada por guias locais.',
        'display_image': 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=1200&q=80',
        'photographer': 'Clube de Montanhismo do Huambo',
        'activity_date': 'Setembro 2026',
        'is_featured': True,
    },
    {
        'title': 'Trilhos Arborizados da Reserva Florestal do Kavongue',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'natureza',
        'category_label': 'Natureza & Vida Selvagem',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Parque da Chiva, Cidade do Huambo',
        'description': 'O pulmão verde da capital provincial, repleto de pinheiros e eucaliptos seculares, ideal para caminhadas matinais e lazer em família.',
        'display_image': 'https://images.unsplash.com/photo-1448375240586-882707db888b?w=1200&q=80',
        'photographer': 'Huambo Verde',
        'activity_date': 'Julho 2026',
        'is_featured': False,
    },
    {
        'title': 'Ombala Grande do Bailundo & Memorial do Rei Ekuikui II',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'cultura',
        'category_label': 'Cultura & Tradição',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Monte Halavala, Bailundo — Huambo',
        'description': 'Sítio histórico sagrado que preserva a memória dos soberanos do Reino do Bailundo e a tradição oral Ovimbundu.',
        'display_image': 'https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=1200&q=80',
        'photographer': 'Arquivo Cultural do Huambo',
        'activity_date': 'Agosto 2026',
        'is_featured': True,
    },
    {
        'title': 'Jardim da Cultura e Arquitetura da Cidade Alta',
        'item_type': 'spot',
        'item_type_label': 'Ponto Turístico',
        'category': 'urbano',
        'category_label': 'Urbano & Património',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Cidade Alta, Huambo',
        'description': 'Avenidas largas e jardins floridos que conferem ao Huambo o título de Cidade Vida no coração de Angola.',
        'display_image': 'https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=1200&q=80',
        'photographer': 'Huambo Viva',
        'activity_date': 'Outubro 2026',
        'is_featured': False,
    },
    {
        'title': 'Danças e Música Tradicional do Planalto Central',
        'item_type': 'activity',
        'item_type_label': 'Actividade Turística / Recreativa',
        'category': 'cultura',
        'category_label': 'Cultura & Tradição',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Centro Cultural do Huambo',
        'description': 'Celebração comunitária com tambores, trajes tradicionais e cânticos em Umbundu durante as festividades da província.',
        'display_image': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1200&q=80',
        'photographer': 'Cultura Huambo',
        'activity_date': 'Setembro 2026',
        'is_featured': False,
    },
    {
        'title': 'Gastronomia das Terras Altas e Kissângua Tradicional',
        'item_type': 'activity',
        'item_type_label': 'Actividade Turística / Recreativa',
        'category': 'gastronomia',
        'category_label': 'Gastronomia & Degustação',
        'province': 'huambo',
        'province_label': 'Huambo',
        'location_name': 'Cidade do Huambo',
        'description': 'Degustação de iguarias típicas do Planalto Central preparadas com produtos agrícolas frescos e acompanhadas por kissângua de milho.',
        'display_image': 'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1200&q=80',
        'photographer': 'Sabores do Planalto',
        'activity_date': 'Outubro 2026',
        'is_featured': False,
    },
]

def gallery_view(request):
    selected_type = request.GET.get('type', '')
    selected_category = request.GET.get('category', '')
    selected_province = request.GET.get('province', '')

    db_items = GalleryItem.objects.all()

    if db_items.exists():
        qs = db_items.select_related('destination')
        if selected_type:
            qs = qs.filter(item_type=selected_type)
        if selected_category:
            qs = qs.filter(category=selected_category)
        if selected_province:
            qs = qs.filter(province=selected_province)

        items = []
        for it in qs:
            items.append({
                'id': it.pk,
                'slug': it.slug,
                'title': it.title,
                'item_type': it.item_type,
                'item_type_label': it.get_item_type_display(),
                'category': it.category,
                'category_label': it.get_category_display(),
                'province': it.province,
                'province_label': it.get_province_display(),
                'location_name': it.location_name,
                'description': it.description,
                'display_image': it.display_image,
                'photographer': it.photographer or 'Destinos da Banda',
                'activity_date': it.activity_date.strftime('%B %Y') if it.activity_date else '',
                'is_featured': it.is_featured,
                'is_demo': it.is_demo,
                'destination_id': it.destination_id,
                'destination_name': it.destination.name if it.destination else it.title,
            })
    else:
        items = list(FALLBACK_GALLERY_ITEMS)
        if selected_type:
            items = [x for x in items if x['item_type'] == selected_type]
        if selected_category:
            items = [x for x in items if x['category'] == selected_category]
        if selected_province:
            items = [x for x in items if x['province'] == selected_province]

    context = {
        'page_title': 'Galeria de Pontos Turísticos e Actividades',
        'items': items,
        'total_count': len(items),
        'selected_type': selected_type,
        'selected_category': selected_category,
        'selected_province': selected_province,
        'provinces': GalleryItem.PROVINCE_CHOICES,
        'categories': GalleryItem.CATEGORY_CHOICES,
        'is_filtered': bool(selected_type or selected_category or selected_province),
    }
    return render(request, 'gallery/gallery.html', context)
