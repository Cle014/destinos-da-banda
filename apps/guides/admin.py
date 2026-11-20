from django.contrib import admin
from django.utils.html import format_html
from .models import GuiaTuristico, Especialidade, AvaliacaoGuia

@admin.register(Especialidade)
class EspecialidadeAdmin(admin.ModelAdmin):
    list_display  = ['nome', 'icon', 'color']
    prepopulated_fields = {'slug': ('nome',)}

class AvaliacaoInline(admin.TabularInline):
    model  = AvaliacaoGuia
    extra  = 0
    readonly_fields = ['utilizador', 'classificacao', 'comentario', 'data']
    can_delete = False

@admin.register(GuiaTuristico)
class GuiaTuristicoAdmin(admin.ModelAdmin):
    list_display  = ['foto_thumb', 'nome', 'provincia', 'anos_experiencia',
                     'avaliacao_media', 'verificado', 'activo', 'destaque']
    list_filter   = ['provincia', 'verificado', 'activo', 'destaque', 'especialidades']
    list_editable = ['verificado', 'activo', 'destaque']
    search_fields = ['nome', 'municipio', 'biografia']
    prepopulated_fields = {'slug': ('nome',)}
    filter_horizontal = ['especialidades', 'destinos']
    readonly_fields = ['avaliacao_media', 'total_avaliacoes', 'created_at', 'updated_at']
    inlines = [AvaliacaoInline]

    fieldsets = [
        ('Identidade', {'fields': ['nome', 'slug', 'foto', 'biografia']}),
        ('Localização', {'fields': ['provincia', 'municipio']}),
        ('Profissional', {'fields': ['anos_experiencia', 'idiomas', 'especialidades',
                                     'destinos', 'certificacoes', 'preco_medio']}),
        ('Contactos', {'fields': ['telefone', 'whatsapp', 'email', 'instagram', 'facebook']}),
        ('Estado', {'fields': ['verificado', 'activo', 'destaque']}),
        ('Estatísticas', {'fields': ['avaliacao_media', 'total_avaliacoes',
                                     'created_at', 'updated_at'],
                          'classes': ['collapse']}),
    ]

    def foto_thumb(self, obj):
        if obj.foto:
            return format_html('<img src="{}" style="width:36px;height:36px;'
                               'border-radius:50%;object-fit:cover;">', obj.foto.url)
        return '—'
    foto_thumb.short_description = ''

@admin.register(AvaliacaoGuia)
class AvaliacaoGuiaAdmin(admin.ModelAdmin):
    list_display  = ['guia', 'utilizador', 'classificacao', 'data']
    list_filter   = ['classificacao']
    readonly_fields = ['data']
