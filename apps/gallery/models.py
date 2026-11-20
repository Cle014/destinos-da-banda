from django.db import models
from django.utils.text import slugify

class GalleryItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('spot', 'Ponto Turístico'),
        ('activity', 'Actividade Turística / Recreativa'),
    ]

    CATEGORY_CHOICES = [
        ('natureza', 'Natureza & Vida Selvagem'),
        ('praia', 'Praias & Costa'),
        ('aventura', 'Aventura & Desporto'),
        ('cultura', 'Cultura & Tradição'),
        ('gastronomia', 'Gastronomia & Degustação'),
        ('urbano', 'Urbano & Património'),
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

    title = models.CharField(max_length=200, verbose_name='Título')
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, default='spot', verbose_name='Tipo de Registo')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='natureza', verbose_name='Categoria')
    province = models.CharField(max_length=30, choices=PROVINCE_CHOICES, verbose_name='Província')
    location_name = models.CharField(max_length=200, verbose_name='Local / Ponto de Referência')
    description = models.TextField(verbose_name='Breve Descrição')
    image = models.ImageField(upload_to='gallery/', blank=True, null=True, verbose_name='Fotografia')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Imagem (externa)')
    photographer = models.CharField(max_length=150, blank=True, verbose_name='Crédito / Fotógrafo')
    activity_date = models.DateField(blank=True, null=True, verbose_name='Data da Actividade / Registo')
    destination = models.ForeignKey(
        'destinations.Destination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gallery_items',
        verbose_name='Destino Associado (para Adicionar ao Plano)'
    )
    video_url = models.URLField(max_length=500, blank=True, verbose_name='URL de Vídeo (opcional)')
    is_demo = models.BooleanField(default=False, verbose_name='Registo Demo')
    is_featured = models.BooleanField(default=False, verbose_name='Em Destaque')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Ordem de exibição')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Item da Galeria'
        verbose_name_plural = 'Itens da Galeria'
        ordering = ['-is_featured', 'order', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_item_type_display()}) - {self.get_province_display()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'foto'
            slug = base
            counter = 1
            while GalleryItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return 'https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=1200&q=80'
