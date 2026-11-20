# =============================================================
# apps/core/context_processors.py
# =============================================================
# Context processors injectam variáveis em TODOS os templates
# automaticamente, sem precisar passar manualmente nas views.
#
# Uso: qualquer template pode usar {{ site_name }}, {{ version }}
# etc., sem que a view precise de os passar explicitamente.
# =============================================================


from django.conf import settings
from apps.destinations.models import Destination
from apps.accommodations.models import Accommodation
from apps.events.models import Event
from apps.gallery.models import GalleryItem
from apps.guides.models import GuiaTuristico
from apps.routes.models import Route


def get_province_wedge_status(province_code=None):
    """
    Calcula a densidade de oferta por módulo para a província activa.
    Estratégia de Cunha (não super-app): só módulos com oferta >= MIN_MODULE_ITEMS_PER_PROVINCE
    ficam activos; os restantes ficam marcados como 'Em breve'.
    """
    prov = province_code or getattr(settings, 'DEFAULT_ACTIVE_PROVINCE', 'huambo')
    min_threshold = getattr(settings, 'MIN_MODULE_ITEMS_PER_PROVINCE', 5)

    counts = {
        'destinations': Destination.objects.filter(status='published', province=prov).count(),
        'accommodations': Accommodation.objects.filter(is_active=True, province=prov).count(),
        'events': Event.objects.filter(province=prov).count(),
        'gallery': GalleryItem.objects.filter(province=prov).count(),
        'guides': GuiaTuristico.objects.filter(activo=True, provincia=prov).count(),
        'routes': Route.objects.filter(status='published', stops__destination__province=prov).distinct().count(),
    }

    modules = {}
    labels = {
        'destinations': ('Destinos', 'destinations:list', 'fas fa-compass'),
        'accommodations': ('Alojamento', 'accommodations:list', 'fas fa-hotel'),
        'events': ('Eventos', 'events:list', 'fas fa-calendar-alt'),
        'gallery': ('Galeria', 'gallery:index', 'fas fa-images'),
        'guides': ('Guias', 'guides:list', 'fas fa-user-tie'),
    }

    for key, (label, url_name, icon) in labels.items():
        cnt = counts.get(key, 0)
        modules[key] = {
            'key': key,
            'label': label,
            'url_name': url_name,
            'icon': icon,
            'count': cnt,
            'threshold': min_threshold,
            'is_enabled': cnt >= min_threshold,
            'missing': max(0, min_threshold - cnt),
        }

    return {
        'active_province': prov,
        'active_province_label': dict(Destination.PROVINCE_CHOICES).get(prov, 'Huambo'),
        'threshold': min_threshold,
        'counts': counts,
        'modules': modules,
        'enabled_modules_count': sum(1 for m in modules.values() if m['is_enabled']),
    }


def site_context(request):
    """
    Injeta variáveis globais do site em todos os templates,
    incluindo canonical URL sem duplicados, carrinho do plano activo
    e estado da Cunha de Densidade por província.
    """
    active_prov = request.GET.get('province') or request.GET.get('provincia') or getattr(settings, 'DEFAULT_ACTIVE_PROVINCE', 'huambo')
    if active_prov not in dict(Destination.PROVINCE_CHOICES):
        active_prov = getattr(settings, 'DEFAULT_ACTIVE_PROVINCE', 'huambo')

    wedge = get_province_wedge_status(active_prov)

    plan_items = request.session.get('trip_plan_items', [])
    canonical_url = request.build_absolute_uri(request.path) if request else ''

    return {
        'site_name': 'Destinos da Banda',
        'site_tagline': 'Descubra o Huambo como nunca viu',
        'site_version': '2.0.0',
        'site_year': 2026,
        'contact_email': 'info@destinosdabanda.ao',
        'canonical_url': canonical_url,
        'wedge': wedge,
        'plan_items': plan_items,
        'plan_items_count': len(plan_items),
        'social_links': {
            'facebook': '#',
            'instagram': '#',
            'twitter': '#',
            'youtube': '#',
        },
    }
