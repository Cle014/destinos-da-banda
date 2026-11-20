from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.text import slugify
from apps.destinations.models import Destination

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='A cor deve estar no formato hexadecimal #RRGGBB.',
)
ICON_CLASS_VALIDATOR = RegexValidator(
    regex=r'^[a-zA-Z0-9\-\s]+$',
    message='Classe de ícone inválida.',
)


def guide_photo_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        ext = 'jpg'
    slug = slugify(getattr(instance, 'slug', '') or getattr(instance, 'nome', '')) or 'guide'
    return f"guides/{slug}.{ext}"

class Especialidade(models.Model):
    ICON_CHOICES = [
        ('fas fa-leaf',        'Ecoturismo'),
        ('fas fa-landmark',    'Turismo Histórico'),
        ('fas fa-masks-theater','Turismo Cultural'),
        ('fas fa-mountain',    'Turismo de Aventura'),
        ('fas fa-tractor',     'Agroturismo'),
        ('fas fa-camera',      'Fotografia'),
        ('fas fa-water',       'Turismo Aquático'),
        ('fas fa-binoculars',  'Safari & Vida Selvagem'),
        ('fas fa-utensils',    'Gastronomia'),
        ('fas fa-city',        'Turismo Urbano'),
    ]

    nome  = models.CharField(max_length=100, unique=True)
    slug  = models.SlugField(max_length=120, unique=True, blank=True)
    icon  = models.CharField(max_length=60, default='fas fa-star', validators=[ICON_CLASS_VALIDATOR])
    color = models.CharField(max_length=7, default='#2D6A4F', validators=[HEX_COLOR_VALIDATOR])

    class Meta:
        verbose_name = 'Especialidade'
        verbose_name_plural = 'Especialidades'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

class GuiaTuristico(models.Model):
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

    IDIOMA_CHOICES = [
        ('pt', 'Português'),
        ('en', 'Inglês'),
        ('fr', 'Francês'),
        ('es', 'Espanhol'),
        ('de', 'Alemão'),
        ('zh', 'Mandarim'),
        ('ar', 'Árabe'),
        ('ki', 'Kimbundu'),
        ('ky', 'Kikongo'),
        ('umb','Umbundu'),
    ]

    nome              = models.CharField(max_length=200)
    slug              = models.SlugField(max_length=220, unique=True, blank=True)
    foto              = models.ImageField(upload_to=guide_photo_path, blank=True, null=True)
    foto_url          = models.URLField(max_length=500, blank=True, verbose_name='URL da Foto (externa)')
    biografia         = models.TextField()
    provincia         = models.CharField(max_length=30, choices=PROVINCE_CHOICES)
    municipio         = models.CharField(max_length=100, blank=True)
    anos_experiencia  = models.PositiveSmallIntegerField(default=1)
    idiomas           = models.JSONField(default=list, help_text='Lista de códigos ISO: ["pt","en"]')
    especialidades    = models.ManyToManyField(Especialidade, blank=True, related_name='guias')
    destinos          = models.ManyToManyField(Destination, blank=True, related_name='guias',
                                               help_text='Destinos em que este guia opera')
    telefone          = models.CharField(max_length=30, blank=True)
    whatsapp          = models.CharField(max_length=30, blank=True)
    email             = models.EmailField(blank=True)
    instagram         = models.URLField(blank=True)
    facebook          = models.URLField(blank=True)
    certificacoes     = models.TextField(blank=True)
    preco_medio       = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                            help_text='Preço médio por dia (USD - legado)')
    preco_dia_aoa     = models.DecimalField(max_digits=12, decimal_places=2, default=45000,
                                            help_text='Tarifa diária base em Kwanzas (Kz)')
    preco_dia_max_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=65000,
                                            help_text='Tarifa diária máxima em Kwanzas (Kz, grupos/expedições)')
    criterio_verificacao = models.CharField(
        max_length=250,
        default='BI/NIF validado, Carteira Profissional INFOTUR e 3+ referências locais verificadas',
        blank=True,
        verbose_name='Critério de Verificação'
    )
    cancellation_policy = models.CharField(
        max_length=280,
        default='Cancelamento gratuito até 48h antes da saída; reembolso de 70% até 24h.',
        verbose_name='Política de Cancelamento'
    )
    is_demo           = models.BooleanField(default=False, verbose_name='Registo Demo')
    avaliacao_media   = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_avaliacoes  = models.PositiveIntegerField(default=0)
    verificado        = models.BooleanField(default=False)
    activo            = models.BooleanField(default=True)
    destaque          = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Guia Turístico'
        verbose_name_plural = 'Guias Turísticos'
        ordering = ['-destaque', '-avaliacao_media', '-anos_experiencia']

    def __str__(self):
        return f"{self.nome} ({self.get_provincia_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nome)
            slug = base
            i = 1
            while GuiaTuristico.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def recalcular_avaliacao(self):
        avaliacoes = self.avaliacoes.all()
        total = avaliacoes.count()
        if total:
            media = sum(a.classificacao for a in avaliacoes) / total
            GuiaTuristico.objects.filter(pk=self.pk).update(
                avaliacao_media=round(media, 2),
                total_avaliacoes=total,
            )
        else:
            GuiaTuristico.objects.filter(pk=self.pk).update(
                avaliacao_media=0, total_avaliacoes=0
            )

    @property
    def display_image(self):
        if self.foto:
            return self.foto.url
        if self.foto_url:
            return self.foto_url
        return ''

    @property
    def idiomas_display(self):
        mapping = dict(self.IDIOMA_CHOICES)
        return [mapping.get(c, c) for c in (self.idiomas or [])]

    @property
    def estrelas_inteiras(self):
        return int(self.avaliacao_media)

    @property
    def tem_meia_estrela(self):
        return (self.avaliacao_media - self.estrelas_inteiras) >= 0.5

    @property
    def formatted_price_range_aoa(self):
        min_p = float(self.preco_dia_aoa or 0)
        max_p = float(self.preco_dia_max_aoa or 0)
        if max_p > min_p:
            return f"{min_p:,.0f} Kz – {max_p:,.0f} Kz / dia".replace(',', ' ')
        return f"{min_p:,.0f} Kz / dia".replace(',', ' ')

    @property
    def formatted_base_price_aoa(self):
        min_p = float(self.preco_dia_aoa or 0)
        return f"{min_p:,.0f} Kz".replace(',', ' ')

class AvaliacaoGuia(models.Model):
    guia          = models.ForeignKey(GuiaTuristico, on_delete=models.CASCADE, related_name='avaliacoes')
    utilizador    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='avaliacoes_guias')
    booking_reference = models.CharField(max_length=24, blank=True, verbose_name='Código de Reserva Concluída')
    reviewer_name = models.CharField(max_length=150, blank=True, verbose_name='Nome do Viajante Verificado')
    classificacao = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    pontualidade  = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    simpatia      = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    conhecimento  = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    organizacao   = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)], default=5
    )
    comentario    = models.TextField(blank=True)
    data          = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        ordering = ['-data']

    def __str__(self):
        autor = self.reviewer_name or (self.utilizador.username if self.utilizador else 'Viajante')
        return f"{autor} ({self.booking_reference}) → {self.guia.nome} ({self.classificacao}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.guia.recalcular_avaliacao()
