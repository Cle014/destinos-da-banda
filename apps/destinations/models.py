import uuid

from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify
import os

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='A cor deve estar no formato hexadecimal #RRGGBB.',
)
ICON_CLASS_VALIDATOR = RegexValidator(
    regex=r'^[a-zA-Z0-9\-\s]+$',
    message='Classe de ícone inválida.',
)


def _safe_ext(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return ext if ext in ALLOWED_IMAGE_EXTENSIONS else 'jpg'


def destination_image_path(instance, filename):
    """
    Define o caminho de upload das imagens de destinos.
    Organiza por: media/destinations/<slug>/<filename>
    Isto evita acumulação de ficheiros numa única pasta.
    """
    ext = _safe_ext(filename)
    slug = slugify(getattr(instance, 'slug', '') or getattr(instance, 'name', '')) or 'destino'
    safe_name = f"{slug}.{ext}"
    return os.path.join('destinations', safe_name)

def destination_gallery_path(instance, filename):
    """Caminho para imagens da galeria do destino."""
    ext = _safe_ext(filename)
    safe_name = f"gallery_{instance.pk or 'new'}.{ext}"
    dest_slug = slugify(getattr(instance.destination, 'slug', '')) or 'destino'
    return os.path.join('destinations', dest_slug, safe_name)

class Category(models.Model):
    """
    Categoria turística — ex: Praias, Parques Naturais, História.
    Simples e reutilizável. Um destino pode ter uma categoria principal.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nome',
        help_text='Ex: Praias, Parques Naturais, História & Cultura'
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
        blank=True,
        verbose_name='Slug (URL)',
        help_text='Gerado automaticamente a partir do nome'
    )

    icon = models.CharField(
        max_length=60,
        default='fas fa-map-marker-alt',
        validators=[ICON_CLASS_VALIDATOR],
        verbose_name='Ícone Font Awesome'
    )

    color = models.CharField(
        max_length=7,
        default='#006B3C',
        validators=[HEX_COLOR_VALIDATOR],
        verbose_name='Cor (hex)'
    )

    description = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Ordem de exibição'
    )

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def destination_count(self):
        """Número de destinos publicados nesta categoria."""
        return self.destinations.filter(status='published').count()

class Destination(models.Model):
    """
    Destino turístico — o modelo central do sistema.
    Contém toda a informação sobre um local turístico angolano.
    """

    STATUS_CHOICES = [
        ('draft',     'Rascunho'),
        ('published', 'Publicado'),
        ('archived',  'Arquivado'),
    ]

    PROVINCE_CHOICES = [
        ('bengo',          'Bengo'),
        ('benguela',       'Benguela'),
        ('bie',            'Bié'),
        ('cabinda',        'Cabinda'),
        ('cuando_cubango', 'Cuando Cubango'),
        ('cuanza_norte',   'Cuanza Norte'),
        ('cuanza_sul',     'Cuanza Sul'),
        ('cunene',         'Cunene'),
        ('huambo',         'Huambo'),
        ('huila',          'Huíla'),
        ('luanda',         'Luanda'),
        ('lunda_norte',    'Lunda Norte'),
        ('lunda_sul',      'Lunda Sul'),
        ('malanje',        'Malanje'),
        ('moxico',         'Moxico'),
        ('namibe',         'Namibe'),
        ('uge',            'Uíge'),
        ('zaire',          'Zaíre'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name='Nome do destino'
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        verbose_name='Slug (URL)',
        help_text='Gerado automaticamente. Ex: quedas-de-kalandula'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,  # Se a categoria for apagada, o destino fica sem categoria (não é apagado)
        null=True,
        blank=True,
        related_name='destinations',
        verbose_name='Categoria'
    )

    province = models.CharField(
        max_length=30,
        choices=PROVINCE_CHOICES,
        verbose_name='Província'
    )

    short_description = models.CharField(
        max_length=300,
        verbose_name='Descrição curta',
        help_text='Usada nos cards da listagem (máx. 300 caracteres)'
    )

    description = models.TextField(
        verbose_name='Descrição completa',
        help_text='Descrição detalhada para a página do destino'
    )

    image = models.ImageField(
        upload_to=destination_image_path,
        blank=True,
        null=True,
        verbose_name='Imagem principal',
        help_text='Imagem principal do destino (recomendado: 1200x800px)'
    )

    image_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='URL da Imagem (externa)'
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Latitude',
        help_text='Ex: -9.004553 (formato decimal)'
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Longitude',
        help_text='Ex: 16.339656 (formato decimal)'
    )

    address = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Endereço / Localização'
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Estado'
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name='Destaque',
        help_text='Mostrar na home page como destino em destaque'
    )

    visit_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de visitas',
        help_text='Incrementado automaticamente a cada visita'
    )

    best_time_to_visit = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Melhor época para visitar'
    )

    entry_fee = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Custo de entrada',
        help_text='Ex: Gratuito / 500 AOA / Variável'
    )

    entry_fee_min_aoa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Entrada mín. (Kz)'
    )

    entry_fee_max_aoa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Entrada máx. (Kz)'
    )

    is_verified = models.BooleanField(
        default=True,
        verbose_name='Verificado'
    )

    verification_criteria = models.CharField(
        max_length=250,
        default='Coordenadas GPS, acesso rodoviário e condições de visita validados localmente',
        blank=True,
        verbose_name='Critério de verificação'
    )

    is_demo = models.BooleanField(
        default=False,
        verbose_name='Registo de Demonstração (Demo)'
    )

    # Campos para Visitas Guiadas & Agroturismo (Fazendas, Comunidades e Experiências Rurais)
    activities_available = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Actividades Disponíveis',
        help_text='Ex: ["Colheita de Café", "Degustação Rural", "Trilho Agrícola"]'
    )
    visit_duration = models.CharField(
        max_length=100,
        blank=True,
        default='Meio dia (3 a 4 horas)',
        verbose_name='Duração da Visita'
    )
    max_visitors = models.PositiveSmallIntegerField(
        default=20,
        verbose_name='Capacidade Máxima por Visita (Vagas/Dia)'
    )
    visit_conditions = models.TextField(
        blank=True,
        verbose_name='Condições de Visita e Recomendações'
    )
    host_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Responsável / Anfitrião ou Fazenda'
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='Telefone de Reserva / Anfitrião'
    )
    contact_whatsapp = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='WhatsApp do Anfitrião'
    )
    video_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Vídeo Explicativo (URL)'
    )
    historical_cultural_context = models.TextField(
        blank=True,
        verbose_name='Contexto Histórico, Cultural ou Agrícola'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado em')

    class Meta:
        verbose_name = 'Destino'
        verbose_name_plural = 'Destinos'
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['province']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_province_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Destination.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def increment_visits(self):
        """
        Incrementa o contador de visitas.
        Usando update() em vez de save() para evitar race conditions
        em ambientes com múltiplos utilizadores simultâneos.
        """
        Destination.objects.filter(pk=self.pk).update(
            visit_count=models.F('visit_count') + 1
        )

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return 'https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=800&q=80'

    @property
    def has_coordinates(self):
        """Verifica se o destino tem coordenadas para o mapa."""
        return self.latitude is not None and self.longitude is not None

    @property
    def formatted_fee_range_aoa(self):
        """Retorna faixa numérica explícita em Kz."""
        min_v = float(self.entry_fee_min_aoa or 0)
        max_v = float(self.entry_fee_max_aoa or 0)
        if min_v <= 0 and max_v <= 0:
            return '0 Kz (Acesso Gratuito)'
        if max_v > min_v:
            return f"{min_v:,.0f} Kz – {max_v:,.0f} Kz".replace(',', ' ')
        return f"{min_v:,.0f} Kz".replace(',', ' ')

    def get_available_visit_spots(self, visit_date=None):
        """Calcula vagas disponíveis para visita numa data específica."""
        qs = self.visit_bookings.filter(status__in=['pending', 'confirmed'])
        if visit_date:
            qs = qs.filter(visit_date=visit_date)
        occupied = sum(b.participants_count for b in qs)
        return max(0, (self.max_visitors or 20) - occupied)

class DestinationImage(models.Model):
    """
    Imagens adicionais de um destino — galeria fotográfica.
    Um destino pode ter múltiplas imagens além da imagem principal.
    """

    destination = models.ForeignKey(
        Destination,
        on_delete=models.CASCADE,  # Se o destino for apagado, as imagens também
        related_name='gallery',
        verbose_name='Destino'
    )

    image = models.ImageField(
        upload_to=destination_gallery_path,
        verbose_name='Imagem'
    )

    caption = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Legenda'
    )

    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Ordem'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Imagem da Galeria'
        verbose_name_plural = 'Imagens da Galeria'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"Imagem de {self.destination.name} ({self.order})"


class DestinationVisitBooking(models.Model):
    """Reserva de visita guiada ou experiência de agroturismo num destino."""
    STATUS_CHOICES = [
        ('pending', 'Pendente de Confirmação'),
        ('confirmed', 'Confirmada'),
        ('completed', 'Realizada'),
        ('cancelled', 'Cancelada'),
    ]

    reference_code = models.CharField(max_length=20, unique=True, editable=False, verbose_name='Código de Visita')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='visit_bookings', verbose_name='Destino / Fazenda')
    visitor_name = models.CharField(max_length=150, verbose_name='Nome do Visitante')
    visitor_email = models.EmailField(verbose_name='Email')
    visitor_phone = models.CharField(max_length=30, verbose_name='Telefone / WhatsApp')
    visit_date = models.DateField(verbose_name='Data da Visita')
    participants_count = models.PositiveSmallIntegerField(default=2, verbose_name='Nº de Participantes')
    total_price_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total (Kz)')
    notes = models.TextField(blank=True, verbose_name='Observações')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed', verbose_name='Estado')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva de Visita / Agroturismo'
        verbose_name_plural = 'Reservas de Visitas / Agroturismo'
        ordering = ['-created_at']

    def __str__(self):
        return f"Visita {self.reference_code} — {self.visitor_name} ({self.destination.name})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            code = f"VS-{uuid.uuid4().hex[:6].upper()}"
            while DestinationVisitBooking.objects.filter(reference_code=code).exclude(pk=self.pk).exists():
                code = f"VS-{uuid.uuid4().hex[:6].upper()}"
            self.reference_code = code
        unit_fee = float(self.destination.entry_fee_min_aoa or 0)
        self.total_price_aoa = unit_fee * (self.participants_count or 1)
        super().save(*args, **kwargs)


class CulturalArticle(models.Model):
    """
    Blog Cultural — Histórias, Cultura, Património, Gastronomia e Memórias dos Destinos.
    Integrado com Destinos, Visitas, Agroturismo e Tours/Experiências.
    """
    TOPIC_CHOICES = [
        ('historia', 'História dos Lugares'),
        ('cultura', 'Cultura & Tradições'),
        ('patrimonio', 'Património & Arquitectura'),
        ('gastronomia', 'Gastronomia & Sabores'),
        ('natureza', 'Natureza & Biodiversidade'),
        ('agroturismo', 'Agroturismo & Vida Rural'),
        ('memorias', 'Histórias, Comunidades & Personalidades'),
        ('curiosidades', 'Curiosidades & Importância Turística'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Rascunho'),
        ('published', 'Publicado'),
    ]

    title = models.CharField(max_length=220, verbose_name='Título do Artigo')
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    subtitle = models.CharField(max_length=300, blank=True, verbose_name='Subtítulo Editorial')
    topic = models.CharField(max_length=30, choices=TOPIC_CHOICES, default='cultura', verbose_name='Tema Principal')
    province = models.CharField(max_length=30, choices=Destination.PROVINCE_CHOICES, default='huambo', verbose_name='Província')
    location_name = models.CharField(max_length=150, blank=True, verbose_name='Localização Específica')

    destination = models.ForeignKey(
        Destination,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cultural_articles',
        verbose_name='Destino Relacionado'
    )
    related_tour = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cultural_articles',
        verbose_name='Tour / Experiência Relacionada'
    )

    author_name = models.CharField(max_length=120, default='Redacção Cultural Destinos da Banda', verbose_name='Autor(a)')
    author_role = models.CharField(max_length=120, blank=True, default='Investigação & Património Local', verbose_name='Cargo / Especialidade do Autor')
    reading_time_minutes = models.PositiveSmallIntegerField(default=4, verbose_name='Tempo de Leitura (min)')

    summary = models.TextField(verbose_name='Introdução / Resumo Editorial')
    content = models.TextField(verbose_name='Corpo do Artigo')
    sections = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Secções Estruturadas',
        help_text='Lista JSON opcional de secções [{"heading": "...", "body": "...", "quote": "..."}]'
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Etiquetas / Tags',
        help_text='Ex: ["Planalto Central", "Reino do Bailundo", "Tradição"]'
    )

    image = models.ImageField(upload_to='articles/', blank=True, null=True, verbose_name='Imagem Principal')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Imagem Principal')
    image_caption = models.CharField(max_length=220, blank=True, verbose_name='Legenda da Fotografia')
    photographer_credit = models.CharField(max_length=150, blank=True, default='Arquivo Destinos da Banda', verbose_name='Créditos Fotográficos')
    video_url = models.URLField(max_length=500, blank=True, verbose_name='Vídeo Documental / Explicativo (URL)')
    gallery_images = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Galeria Editorial do Artigo',
        help_text='Lista [{"url": "...", "caption": "...", "credit": "..."}]'
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='published', verbose_name='Estado')
    is_featured = models.BooleanField(default=False, verbose_name='Artigo em Destaque')
    view_count = models.PositiveIntegerField(default=0, verbose_name='Leituras')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Artigo Cultural'
        verbose_name_plural = 'Artigos Culturais (Blog)'
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_topic_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'artigo-cultural'
            slug = base
            idx = 1
            while CulturalArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{idx}"
                idx += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        if self.destination:
            return self.destination.display_image
        return 'https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1200&q=80'
