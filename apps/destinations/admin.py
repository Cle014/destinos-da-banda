# =============================================================
# apps/destinations/admin.py — PAINEL DE ADMINISTRAÇÃO
# =============================================================
# Configuração do painel admin Django para gerir destinos.
# Permite criar, editar, filtrar e pesquisar destinos
# directamente no browser em /admin/
# =============================================================

from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Destination, DestinationImage


# =============================================================
# INLINE: Imagens da galeria dentro do destino
# =============================================================
class DestinationImageInline(admin.TabularInline):
    """
    Permite adicionar imagens da galeria directamente
    na página de edição do destino — sem sair da página.
    """
    model = DestinationImage
    extra = 3          # Mostrar 3 campos vazios por padrão
    max_num = 20       # Máximo de 20 imagens por destino
    fields = ['image', 'caption', 'order']


# =============================================================
# ADMIN: Category
# =============================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'icon', 'color_preview', 'destination_count', 'order']
    list_editable = ['order']
    prepopulated_fields = {'slug': ('name',)}  # Gera slug ao escrever o nome
    search_fields = ['name']

    def color_preview(self, obj):
        """Mostra um quadrado colorido com a cor da categoria."""
        import re
        safe_color = obj.color if re.match(r'^#[0-9A-Fa-f]{6}$', obj.color or '') else '#006B3C'
        return format_html(
            '<div style="width:24px; height:24px; background:{}; '
            'border-radius:4px; border:1px solid #ddd;"></div>',
            safe_color
        )
    color_preview.short_description = 'Cor'

    def destination_count(self, obj):
        return obj.destination_count
    destination_count.short_description = 'Destinos'


# =============================================================
# ADMIN: Destination
# =============================================================
@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    # Colunas na listagem
    list_display = [
        'name', 'province', 'category',
        'status', 'is_featured',
        'visit_count', 'created_at'
    ]

    # Campos editáveis directamente na listagem
    list_editable = ['status', 'is_featured']

    # Filtros na barra lateral
    list_filter = ['status', 'is_featured', 'province', 'category']

    # Pesquisa por estes campos
    search_fields = ['name', 'short_description', 'description']

    # Gerar slug automaticamente ao escrever o nome
    prepopulated_fields = {'slug': ('name',)}

    # Agrupamento dos campos no formulário de edição
    fieldsets = [
        ('Informação Principal', {
            'fields': ['name', 'slug', 'category', 'province', 'status', 'is_featured']
        }),
        ('Descrições', {
            'fields': ['short_description', 'description']
        }),
        ('Imagem Principal', {
            'fields': ['image']
        }),
        ('Localização no Mapa', {
            'fields': ['address', 'latitude', 'longitude'],
            'description': 'Coordenadas para o mapa interactivo (Fase 4)'
        }),
        ('Informações Práticas', {
            'fields': ['best_time_to_visit', 'entry_fee'],
            'classes': ['collapse']  # Secção colapsável
        }),
        ('Estatísticas (só leitura)', {
            'fields': ['visit_count'],
            'classes': ['collapse']
        }),
    ]

    # Campos só de leitura — não editáveis no admin
    readonly_fields = ['visit_count', 'created_at', 'updated_at']

    # Galeria de imagens integrada
    inlines = [DestinationImageInline]

    # Paginação — 20 por página
    list_per_page = 20

    # Ordenação padrão na listagem
    ordering = ['-created_at']
