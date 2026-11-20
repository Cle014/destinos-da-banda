import json
import os
import re
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

from apps.gallery.models import GalleryItem
from apps.routes.models import Route, RouteStop
from apps.accommodations.models import Accommodation, RoomType, Booking, TripOrder
from apps.destinations.models import Destination, Category, CulturalArticle, DestinationVisitBooking
from apps.events.models import Event, EventBooking
from apps.guides.models import GuiaTuristico, Especialidade

ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
ALLOWED_UPLOAD_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
UNSAFE_URL_CHARS_RE = re.compile(r'[\'"()<>\\\r\n;]')
HEX_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
ICON_CLASS_RE = re.compile(r'^[a-zA-Z0-9\-\s]+$')


class ImageSizeMixin:
    """Valida tamanho, extensão, MIME type de uploads e segurança de URLs externas."""

    def clean(self):
        cleaned = super().clean()
        limit_mb = getattr(settings, 'MAX_UPLOAD_IMAGE_MB', 8)
        for name, value in list(cleaned.items()):
            if isinstance(value, UploadedFile):
                if value.size > limit_mb * 1024 * 1024:
                    self.add_error(name, f'O ficheiro excede o limite de {limit_mb} MB.')
                ext = os.path.splitext(value.name or '')[1].lower()
                if ext not in ALLOWED_UPLOAD_EXTENSIONS:
                    self.add_error(
                        name,
                        'Extensão de ficheiro não permitida. Use JPG, PNG, WEBP ou GIF.',
                    )
                content_type = getattr(value, 'content_type', '')
                if content_type and content_type.lower() not in ALLOWED_UPLOAD_CONTENT_TYPES:
                    self.add_error(
                        name,
                        'Tipo MIME de imagem inválido. Carregue apenas imagens válidas.',
                    )
            elif isinstance(value, str) and value and name.endswith('_url'):
                val_lower = value.strip().lower()
                if not (val_lower.startswith('http://') or val_lower.startswith('https://')):
                    self.add_error(name, 'O URL deve começar por http:// ou https://.')
                elif UNSAFE_URL_CHARS_RE.search(value):
                    self.add_error(name, 'O URL contém caracteres não permitidos.')
        return cleaned


def _unique_slug(model_cls, instance, source_text, fallback):
    if instance.slug:
        return instance.slug
    base_slug = slugify(source_text) or fallback
    slug = base_slug
    idx = 1
    while model_cls.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{idx}"
        idx += 1
    return slug


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'icon', 'color', 'order', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Praias & Costa'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-umbrella-beach'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for opt in ('icon', 'color', 'order'):
            if opt in self.fields:
                self.fields[opt].required = False

    def clean_order(self):
        val = self.cleaned_data.get('order')
        return val if val is not None else 0

    def clean_color(self):
        color = (self.cleaned_data.get('color') or '#006B3C').strip()
        if not HEX_COLOR_RE.match(color):
            raise forms.ValidationError('A cor deve estar no formato hexadecimal #RRGGBB.')
        return color

    def clean_icon(self):
        icon = (self.cleaned_data.get('icon') or 'fas fa-map-marker-alt').strip()
        if not ICON_CLASS_RE.match(icon):
            raise forms.ValidationError('Classe de ícone inválida (apenas letras, números, espaços e hífens).')
        return icon

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Category, instance, instance.name, 'categoria')
        if commit:
            instance.save()
        return instance


class DestinationQuickForm(ImageSizeMixin, forms.ModelForm):
    activities_available = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Colheita de Café, Degustação Rural, Trilho Guiado'}),
    )

    class Meta:
        model = Destination
        fields = [
            'name', 'category', 'province', 'address',
            'short_description', 'description', 'historical_cultural_context',
            'activities_available', 'visit_duration', 'max_visitors',
            'host_name', 'contact_phone', 'contact_whatsapp', 'visit_conditions',
            'image', 'image_url', 'video_url',
            'best_time_to_visit', 'entry_fee', 'entry_fee_min_aoa',
            'latitude', 'longitude',
            'status', 'is_featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Miradouro da Lua'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Município / referência geográfica'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resumo apelativo para os cartões (máx. 300 caracteres)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrição completa do destino, história e o que visitar...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/foto.jpg (opcional se carregar ficheiro)'}),
            'best_time_to_visit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Maio a Setembro (Cacimbo)'}),
            'entry_fee': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Gratuito / 5 000 Kz'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '-9.0738'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '16.0005'}),
            'historical_cultural_context': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Contexto histórico, cultural ou agrícola...'}),
            'visit_duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 4 horas / Meio dia'}),
            'max_visitors': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 20}),
            'host_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Cooperativa Agrícola da Chianga'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'contact_whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'visit_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Condições de visita e recomendações...'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'entry_fee_min_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '500', 'placeholder': '0 se gratuito'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for opt in ('max_visitors', 'entry_fee_min_aoa', 'visit_duration'):
            if opt in self.fields:
                self.fields[opt].required = False
        if self.instance and self.instance.pk and isinstance(self.instance.activities_available, list):
            self.initial['activities_available'] = ', '.join(str(x) for x in self.instance.activities_available)

    def clean_max_visitors(self):
        return self.cleaned_data.get('max_visitors') or 20

    def clean_entry_fee_min_aoa(self):
        return self.cleaned_data.get('entry_fee_min_aoa') or 0

    def clean_activities_available(self):
        val = self.cleaned_data.get('activities_available', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            return [x.strip() for x in val.split(',') if x.strip()]
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Destination, instance, instance.name, 'destino')
        if commit:
            instance.save()
        return instance


class GalleryItemForm(ImageSizeMixin, forms.ModelForm):
    class Meta:
        model = GalleryItem
        fields = [
            'title', 'item_type', 'category', 'province',
            'location_name', 'description', 'image', 'image_url',
            'photographer', 'activity_date', 'is_featured',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Pôr do sol na Fenda da Tundavala'}),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lubango, Huíla'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Breve descrição da foto ou actividade...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/imagem.jpg (opcional se enviar ficheiro)'}),
            'photographer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Fotógrafo João / Turismo Huíla'}),
            'activity_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(GalleryItem, instance, instance.title, 'foto')
        if commit:
            instance.save()
        return instance


class RouteForm(ImageSizeMixin, forms.ModelForm):
    class Meta:
        model = Route
        fields = [
            'name', 'short_description', 'description',
            'duration_days', 'difficulty', 'status',
            'image', 'image_url', 'is_featured',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Rota das Quedas e Serras'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resumo em 1 linha (ex: De Luanda a Malanje em 3 dias)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrição completa do roteiro, dicas de paragens e o que esperar...'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/rota.jpg (opcional)'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Route, instance, instance.name, 'rota')
        if commit:
            instance.save()
        return instance


class RouteStopForm(forms.ModelForm):
    class Meta:
        model = RouteStop
        fields = ['route', 'destination', 'day', 'order', 'notes']
        widgets = {
            'route': forms.Select(attrs={'class': 'form-select'}),
            'destination': forms.Select(attrs={'class': 'form-select'}),
            'day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notas desta paragem no itinerário'}),
        }


class AccommodationForm(ImageSizeMixin, forms.ModelForm):
    amenities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ex: wifi, piscina, ar_condicionado, pequeno_almoco, estacionamento',
        }),
        help_text='Indique as comodidades separadas por vírgula',
    )
    max_guests = forms.IntegerField(required=False, initial=2, min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    bedrooms = forms.IntegerField(required=False, initial=1, min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    bathrooms = forms.IntegerField(required=False, initial=1, min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    total_units = forms.IntegerField(required=False, initial=1, min_value=1, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Accommodation
        fields = [
            'name', 'accommodation_type', 'province', 'city', 'address',
            'latitude', 'longitude',
            'price_per_night_aoa', 'price_per_night_usd',
            'max_guests', 'bedrooms', 'bathrooms', 'total_units', 'amenities',
            'house_rules', 'booking_conditions',
            'image', 'image_url', 'contact_phone', 'contact_whatsapp', 'contact_email',
            'short_description', 'description', 'is_featured', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Hotel Baía Luanda ou Lodge do Kissama'}),
            'accommodation_type': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Luanda, Benguela, Lubango...'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Avenida 4 de Fevereiro, Marginal'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '-12.7761'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001', 'placeholder': '15.7392'}),
            'price_per_night_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '500', 'placeholder': 'Ex: 45000'}),
            'price_per_night_usd': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'placeholder': 'Ex: 50 (opcional)'}),
            'house_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Horários de check-in/out, animais, silêncio...'}),
            'booking_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Condições de reserva e cancelamento...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/hotel.jpg (opcional)'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'contact_whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'reservas@alojamento.ao'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Resumo curto com localização e estilo...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descrição detalhada dos serviços e espaço...'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and isinstance(self.instance.amenities, list):
            self.initial['amenities'] = ', '.join(str(x) for x in self.instance.amenities)

    def clean_max_guests(self):
        return self.cleaned_data.get('max_guests') or 2

    def clean_bedrooms(self):
        return self.cleaned_data.get('bedrooms') or 1

    def clean_bathrooms(self):
        return self.cleaned_data.get('bathrooms') or 1

    def clean_total_units(self):
        return self.cleaned_data.get('total_units') or 1

    def clean_amenities(self):
        val = self.cleaned_data.get('amenities', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return []
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [item.strip() for item in val.split(',') if item.strip()]
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Accommodation, instance, instance.name, 'alojamento')
        if commit:
            instance.save()
        return instance


class EventQuickForm(ImageSizeMixin, forms.ModelForm):
    location_venue = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Baía de Moçâmedes, Namibe'}))
    price_aoa = forms.DecimalField(required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 se gratuito'}))
    organizer_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Associação de Turismo'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

    def clean_location_venue(self):
        return self.cleaned_data.get('location_venue') or 'Angola'

    def clean_price_aoa(self):
        p = self.cleaned_data.get('price_aoa')
        return p if p is not None else 0

    def clean_organizer_name(self):
        return self.cleaned_data.get('organizer_name') or 'Destinos da Banda'

    def clean_description(self):
        return self.cleaned_data.get('description') or self.cleaned_data.get('title', '')

    included_services = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Transporte 4x4, Guia Certificado, Almoço Rural, Seguro'}),
    )

    class Meta:
        model = Event
        fields = [
            'title', 'subtitle', 'activity_type', 'category', 'province',
            'destination', 'guide', 'partners',
            'location_venue', 'start_date', 'end_date', 'time_schedule',
            'duration', 'max_participants', 'min_participants',
            'is_free', 'price_aoa', 'organizer_name', 'contact_phone',
            'contact_whatsapp', 'image', 'image_url', 'video_url',
            'description', 'historical_cultural_context', 'itinerary',
            'included_services', 'participation_conditions',
            'status', 'is_featured',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Festas do Mar de Moçâmedes'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subtítulo curto (opcional)'}),
            'activity_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'destination': forms.Select(attrs={'class': 'form-select'}),
            'guide': forms.Select(attrs={'class': 'form-select'}),
            'partners': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Cooperativa Local, INFOTUR'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_schedule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 09:00 - 18:00'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1 Dia (6 horas)'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 20}),
            'min_participants': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'is_free': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'contact_whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/evento.jpg'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'historical_cultural_context': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Contexto histórico, cultural ou natural...'}),
            'itinerary': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Etapas e horários da tour ou actividade...'}),
            'participation_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Condições de participação e o que levar...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for opt in ('max_participants', 'min_participants', 'duration'):
            if opt in self.fields:
                self.fields[opt].required = False
        if self.instance and self.instance.pk and isinstance(self.instance.included_services, list):
            self.initial['included_services'] = ', '.join(str(x) for x in self.instance.included_services)

    def clean_max_participants(self):
        return self.cleaned_data.get('max_participants') or 20

    def clean_min_participants(self):
        return self.cleaned_data.get('min_participants') or 1

    def clean_included_services(self):
        val = self.cleaned_data.get('included_services', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            return [x.strip() for x in val.split(',') if x.strip()]
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Event, instance, instance.title, 'evento')
        if commit:
            instance.save()
        return instance


class GuideForm(ImageSizeMixin, forms.ModelForm):
    idiomas = forms.CharField(
        required=False,
        initial='pt, en',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: pt, en, fr, umb'}),
        help_text='Códigos separados por vírgula (pt, en, fr, es, ki, umb)',
    )

    class Meta:
        model = GuiaTuristico
        fields = [
            'nome', 'provincia', 'municipio', 'anos_experiencia',
            'idiomas', 'especialidades', 'destinos',
            'preco_dia_aoa', 'preco_dia_max_aoa', 'preco_medio',
            'telefone', 'whatsapp', 'email',
            'certificacoes', 'biografia',
            'foto', 'foto_url',
            'verificado', 'activo', 'destaque',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Mateus Kiala'}),
            'provincia': forms.Select(attrs={'class': 'form-select'}),
            'municipio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lubango, Kalandula...'}),
            'anos_experiencia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 3}),
            'especialidades': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'destinos': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'preco_dia_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'placeholder': 'Ex: 45000 (Kz/dia)'}),
            'preco_dia_max_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'placeholder': 'Ex: 65000 (Kz/dia máx.)'}),
            'preco_medio': forms.NumberInput(attrs={'class': 'form-control', 'step': '5', 'placeholder': 'Ex: 65 (USD/dia)'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'guia@destinosdabanda.ao'}),
            'certificacoes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Guia Certificado INFOTUR'}),
            'biografia': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Apresentação profissional e experiência do guia...'}),
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'foto_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://exemplo.com/foto-guia.jpg'}),
            'verificado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'destaque': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for opt in ('preco_dia_aoa', 'preco_dia_max_aoa'):
            if opt in self.fields:
                self.fields[opt].required = False
        if self.instance and self.instance.pk and isinstance(self.instance.idiomas, list):
            self.initial['idiomas'] = ', '.join(str(x) for x in self.instance.idiomas)

    def clean_preco_dia_aoa(self):
        val = self.cleaned_data.get('preco_dia_aoa')
        return val if val is not None else 45000

    def clean_preco_dia_max_aoa(self):
        val = self.cleaned_data.get('preco_dia_max_aoa')
        return val if val is not None else 65000

    def clean_idiomas(self):
        val = self.cleaned_data.get('idiomas', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            items = [x.strip().lower() for x in val.split(',') if x.strip()]
            return items or ['pt']
        return ['pt']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(GuiaTuristico, instance, instance.nome, 'guia')
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class RoomTypeForm(ImageSizeMixin, forms.ModelForm):
    amenities = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Wi-Fi, Ar Condicionado, Pequeno-Almoço, Varanda'}),
    )

    class Meta:
        model = RoomType
        fields = [
            'accommodation', 'name', 'category', 'description',
            'capacity_guests', 'beds_count', 'bed_configuration',
            'amenities', 'price_per_night_aoa', 'total_units',
            'booking_conditions', 'image', 'image_url', 'is_active',
        ]
        widgets = {
            'accommodation': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Suite Executiva Vista Jardim'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'capacity_guests': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 2}),
            'beds_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'bed_configuration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 1 Cama King-Size ou 2 Twin'}),
            'price_per_night_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000'}),
            'total_units': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 5}),
            'booking_conditions': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and isinstance(self.instance.amenities, list):
            self.initial['amenities'] = ', '.join(str(x) for x in self.instance.amenities)

    def clean_amenities(self):
        val = self.cleaned_data.get('amenities', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            return [x.strip() for x in val.split(',') if x.strip()]
        return []


class CulturalArticleForm(ImageSizeMixin, forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: História, Reino do Bailundo, Gastronomia, Planalto'}),
    )

    class Meta:
        model = CulturalArticle
        fields = [
            'title', 'subtitle', 'topic', 'province', 'location_name',
            'destination', 'related_tour',
            'author_name', 'author_role', 'reading_time_minutes',
            'summary', 'content', 'tags',
            'image', 'image_url', 'image_caption', 'photographer_credit',
            'video_url', 'status', 'is_featured',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título editorial do artigo'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subtítulo complementar'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'province': forms.Select(attrs={'class': 'form-select'}),
            'location_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bailundo, Huambo'}),
            'destination': forms.Select(attrs={'class': 'form-select'}),
            'related_tour': forms.Select(attrs={'class': 'form-select'}),
            'author_name': forms.TextInput(attrs={'class': 'form-control'}),
            'author_role': forms.TextInput(attrs={'class': 'form-control'}),
            'reading_time_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 4}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Introdução / Resumo do artigo...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Texto completo do artigo...'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'image_url': forms.URLInput(attrs={'class': 'form-control'}),
            'image_caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Legenda da fotografia'}),
            'photographer_credit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Créditos fotográficos'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and isinstance(self.instance.tags, list):
            self.initial['tags'] = ', '.join(str(x) for x in self.instance.tags)

    def clean_tags(self):
        val = self.cleaned_data.get('tags', '')
        if isinstance(val, list):
            return val
        if isinstance(val, str) and val.strip():
            return [x.strip() for x in val.split(',') if x.strip()]
        return []

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(CulturalArticle, instance, instance.title, 'artigo')
        if commit:
            instance.save()
        return instance


class EspecialidadeForm(forms.ModelForm):
    class Meta:
        model = Especialidade
        fields = ['nome', 'icon', 'color']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ecoturismo'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-leaf'}),
            'color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['icon'].required = False
        self.fields['color'].required = False

    def clean_color(self):
        color = (self.cleaned_data.get('color') or '#2D6A4F').strip()
        if not HEX_COLOR_RE.match(color):
            raise forms.ValidationError('A cor deve estar no formato hexadecimal #RRGGBB.')
        return color

    def clean_icon(self):
        icon = (self.cleaned_data.get('icon') or 'fas fa-star').strip()
        if not ICON_CLASS_RE.match(icon):
            raise forms.ValidationError('Classe de ícone inválida (apenas letras, números, espaços e hífens).')
        return icon

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slug = _unique_slug(Especialidade, instance, instance.nome, 'especialidade')
        if commit:
            instance.save()
        return instance


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'accommodation', 'room_type', 'units_reserved',
            'guest_name', 'guest_email', 'guest_phone',
            'check_in', 'check_out', 'guests_count',
            'status', 'special_requests',
        ]
        widgets = {
            'accommodation': forms.Select(attrs={'class': 'form-select'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'units_reserved': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do hóspede'}),
            'guest_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'hospede@email.com'}),
            'guest_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'check_in': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'check_out': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'guests_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'special_requests': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Pedidos especiais ou observações...'}),
        }

    def clean(self):
        cleaned = super().clean()
        check_in = cleaned.get('check_in')
        check_out = cleaned.get('check_out')
        if check_in and check_out and check_out <= check_in:
            self.add_error('check_out', 'A data de saída deve ser posterior à data de entrada.')
        return cleaned


class EventBookingForm(forms.ModelForm):
    class Meta:
        model = EventBooking
        fields = [
            'event', 'participant_name', 'participant_email', 'participant_phone',
            'selected_date', 'participants_count', 'status', 'special_notes',
        ]
        widgets = {
            'event': forms.Select(attrs={'class': 'form-select'}),
            'participant_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do participante'}),
            'participant_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'participante@email.com'}),
            'participant_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'selected_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'participants_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 1}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'special_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações ou restrições...'}),
        }


class DestinationVisitBookingForm(forms.ModelForm):
    class Meta:
        model = DestinationVisitBooking
        fields = [
            'destination', 'visitor_name', 'visitor_email', 'visitor_phone',
            'visit_date', 'participants_count', 'status', 'notes',
        ]
        widgets = {
            'destination': forms.Select(attrs={'class': 'form-select'}),
            'visitor_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do visitante'}),
            'visitor_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'visitante@email.com'}),
            'visitor_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'participants_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observações sobre a visita...'}),
        }


class TripOrderForm(forms.ModelForm):
    province = forms.ChoiceField(
        choices=Destination.PROVINCE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Província',
    )

    class Meta:
        model = TripOrder
        fields = [
            'province', 'guest_name', 'guest_email', 'guest_phone',
            'start_date', 'end_date', 'travelers_count',
            'payment_method', 'payment_phone', 'payment_status',
            'total_aoa', 'status', 'notes',
        ]
        widgets = {
            'guest_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do viajante'}),
            'guest_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'viajante@email.com'}),
            'guest_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'travelers_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'value': 2}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+244 923 000 000'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'total_aoa': forms.NumberInput(attrs={'class': 'form-control', 'step': '500', 'placeholder': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notas da jornada...'}),
        }

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        end_date = cleaned.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'A data de fim não pode ser anterior à data de início.')
        return cleaned
