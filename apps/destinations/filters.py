# =============================================================
# apps/destinations/filters.py — FILTROS DE PESQUISA
# =============================================================
# Usa django-filter para filtrar destinos por:
# categoria, província, avaliação e estado.
#
# Porquê um ficheiro separado?
# Mantém a view limpa e os filtros reutilizáveis
# (a API REST da Fase 8 usará os mesmos filtros).
# =============================================================

import django_filters
from .models import Destination, Category


class DestinationFilter(django_filters.FilterSet):
    """
    Filtros disponíveis na listagem de destinos.
    Cada campo gera automaticamente um parâmetro na URL.
    Ex: /destinos/?province=malanje&category=praias
    """

    # Pesquisa textual — procura no nome e descrição
    search = django_filters.CharFilter(
        method='filter_search',
        label='Pesquisar'
    )

    # Filtro por categoria (pelo slug)
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category__slug',
        to_field_name='slug',
        label='Categoria'
    )

    # Filtro por província
    province = django_filters.ChoiceFilter(
        choices=Destination.PROVINCE_CHOICES,
        label='Província'
    )

    class Meta:
        model = Destination
        fields = ['category', 'province']

    def filter_search(self, queryset, name, value):
        """
        Pesquisa em múltiplos campos simultaneamente.
        Usa OR para encontrar o valor em qualquer campo.
        """
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value) |
            Q(short_description__icontains=value) |
            Q(description__icontains=value) |
            Q(address__icontains=value)
        )
