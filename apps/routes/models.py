from django.db import models
from django.utils.text import slugify
from apps.destinations.models import Destination

class Route(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy',     'Fácil'),
        ('moderate', 'Moderado'),
        ('hard',     'Difícil'),
    ]

    STATUS_CHOICES = [
        ('draft',     'Rascunho'),
        ('published', 'Publicado'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nome da rota')
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(verbose_name='Descrição')
    short_description = models.CharField(max_length=300, verbose_name='Descrição curta')
    image = models.ImageField(upload_to='routes/', verbose_name='Imagem de capa', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Imagem (externa)')
    duration_days = models.PositiveSmallIntegerField(verbose_name='Duração (dias)', default=1)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='easy')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False, verbose_name='Registo Demo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rota'
        verbose_name_plural = 'Rotas'
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Route.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return ''

    @property
    def destinations_count(self):
        return self.stops.count()

    @property
    def provinces(self):
        return list(
            self.stops.order_by('day', 'order')
            .values_list('destination__province', flat=True)
            .distinct()
        )

class RouteStop(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='route_stops')
    day = models.PositiveSmallIntegerField(verbose_name='Dia', default=1)
    order = models.PositiveSmallIntegerField(verbose_name='Ordem no dia', default=0)
    notes = models.TextField(blank=True, verbose_name='Notas do dia')
    duration_hours = models.PositiveSmallIntegerField(default=2, verbose_name='Duração (horas)')

    class Meta:
        verbose_name = 'Paragem'
        verbose_name_plural = 'Paragens'
        ordering = ['day', 'order']
        unique_together = [['route', 'destination']]

    def __str__(self):
        return f"{self.route.name} — Dia {self.day}: {self.destination.name}"
