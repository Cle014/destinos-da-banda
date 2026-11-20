import uuid
from django.db import models
from django.utils.text import slugify

class Event(models.Model):
    ACTIVITY_TYPE_CHOICES = [
        ('tour', 'Tour & Experiência Turística Guiada'),
        ('turistica', 'Actividade Turística'),
        ('recreativa', 'Actividade Recreativa & Lazer'),
        ('cultural', 'Evento Cultural & Festivo'),
    ]

    CATEGORY_CHOICES = [
        ('aventura', 'Aventura & Desporto'),
        ('cultural', 'Cultura, História & Património'),
        ('gastronomia', 'Gastronomia & Degustação'),
        ('agroturismo', 'Agroturismo & Experiências Rurais'),
        ('musica', 'Música & Festivais'),
        ('natureza', 'Natureza, Montanha & Trilhos'),
        ('praia', 'Náutica & Águas'),
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

    STATUS_CHOICES = [
        ('upcoming', 'Brevemente'),
        ('ongoing', 'A decorrer'),
        ('finished', 'Terminado'),
    ]

    title = models.CharField(max_length=200, verbose_name='Nome do Evento / Actividade')
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=250, blank=True, verbose_name='Subtítulo / Resumo Rápido')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES, default='recreativa', verbose_name='Tipo de Actividade')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='aventura', verbose_name='Categoria')
    province = models.CharField(max_length=30, choices=PROVINCE_CHOICES, verbose_name='Província')
    location_venue = models.CharField(max_length=200, verbose_name='Local / Ponto de Encontro')
    
    start_date = models.DateField(verbose_name='Data de Início')
    end_date = models.DateField(blank=True, null=True, verbose_name='Data de Fim')
    time_schedule = models.CharField(max_length=100, blank=True, verbose_name='Horário', help_text='Ex: 09:00 - 17:00')
    
    is_free = models.BooleanField(default=False, verbose_name='Entrada / Participação Gratuita')
    price_aoa = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Preço Mín. / Ingresso (AOA)')
    price_max_aoa = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Preço Máx. / Ingresso (AOA)')

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitude')
    cancellation_policy = models.CharField(
        max_length=280,
        default='Cancelamento gratuito até 24h antes do evento com reembolso total.',
        verbose_name='Política de Cancelamento'
    )
    is_verified = models.BooleanField(default=True, verbose_name='Evento Verificado')
    verification_criteria = models.CharField(
        max_length=250,
        default='Organizador identificado, licença municipal/cultural e ponto de encontro validados',
        blank=True,
        verbose_name='Critério de Verificação'
    )
    is_demo = models.BooleanField(default=False, verbose_name='Registo Demo')
    
    description = models.TextField(verbose_name='Descrição Completa do Evento')
    organizer_name = models.CharField(max_length=150, verbose_name='Organizador')
    contact_phone = models.CharField(max_length=30, blank=True, verbose_name='Telefone de Contacto')
    contact_whatsapp = models.CharField(max_length=30, blank=True, verbose_name='WhatsApp')
    registration_link = models.URLField(blank=True, verbose_name='Link de Inscrição / Bilhetes')
    
    image = models.ImageField(upload_to='events/', blank=True, null=True, verbose_name='Cartaz / Imagem de Capa')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Imagem')
    video_url = models.URLField(max_length=500, blank=True, verbose_name='Vídeo Explicativo da Tour / Destino')

    # Campos específicos de Tours e Experiências Turísticas
    destination = models.ForeignKey(
        'destinations.Destination',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tours_and_events',
        verbose_name='Destino Turístico Associado'
    )
    guide = models.ForeignKey(
        'guides.GuiaTuristico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='guided_tours',
        verbose_name='Guia Certificado Responsável'
    )
    partners = models.CharField(max_length=250, blank=True, verbose_name='Parceiros & Apoio Local')
    duration = models.CharField(max_length=100, blank=True, default='1 Dia (6 horas)', verbose_name='Duração da Experiência')
    max_participants = models.PositiveSmallIntegerField(default=20, verbose_name='Vagas Totais / Capacidade Máxima')
    min_participants = models.PositiveSmallIntegerField(default=1, verbose_name='Mínimo de Participantes')
    itinerary = models.TextField(blank=True, verbose_name='Itinerário Detalhado da Tour (Etapas e Horários)')
    included_services = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Serviços Incluídos',
        help_text='Ex: ["Transporte 4x4", "Guia Certificado", "Almoço Tradicional", "Seguro"]'
    )
    participation_conditions = models.TextField(
        blank=True,
        verbose_name='Condições de Participação e O Que Levar'
    )
    historical_cultural_context = models.TextField(
        blank=True,
        verbose_name='Contexto Histórico, Cultural ou Natural'
    )
    gallery_images = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Galeria de Fotografias da Tour (URLs)'
    )
    
    is_featured = models.BooleanField(default=False, verbose_name='Evento em Destaque')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='upcoming', verbose_name='Estado')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento & Actividade'
        verbose_name_plural = 'Eventos & Actividades'
        ordering = ['start_date', '-is_featured']

    def __str__(self):
        return f"{self.title} ({self.start_date.strftime('%d/%m/%Y')}) — {self.get_province_display()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'evento'
            slug = base
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
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
        return 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=1200&q=80'

    @property
    def formatted_price(self):
        if self.is_free or self.price_aoa == 0:
            return '0 Kz (Gratuito)'
        min_p = float(self.price_aoa or 0)
        max_p = float(self.price_max_aoa or 0)
        if max_p > min_p:
            return f"{min_p:,.0f} Kz – {max_p:,.0f} Kz".replace(',', ' ')
        return f"{min_p:,.0f} Kz".replace(',', ' ')

    @property
    def booked_participants_count(self):
        return sum(
            b.participants_count
            for b in self.tour_bookings.filter(status__in=['pending', 'confirmed', 'completed'])
        )

    @property
    def available_spots(self):
        if not self.max_participants:
            return 99
        return max(0, self.max_participants - self.booked_participants_count)

    @property
    def availability_badge(self):
        spots = self.available_spots
        if self.status == 'finished' or spots <= 0:
            return ('sold_out', 'Esgotado / Encerrado')
        if spots <= 4:
            return ('last_spots', f'Últimas {spots} vagas!')
        return ('available', f'{spots} vagas disponíveis')


class EventBooking(models.Model):
    """Inscrição / Reserva em Tour ou Experiência Turística com gestão real de vagas."""
    STATUS_CHOICES = [
        ('pending', 'Pendente de Confirmação'),
        ('confirmed', 'Confirmada'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
    ]

    reference_code = models.CharField(max_length=20, unique=True, editable=False, verbose_name='Código de Inscrição')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='tour_bookings', verbose_name='Tour / Experiência')
    participant_name = models.CharField(max_length=150, verbose_name='Nome do Participante')
    participant_email = models.EmailField(verbose_name='Email')
    participant_phone = models.CharField(max_length=30, verbose_name='Telefone / WhatsApp')
    selected_date = models.DateField(null=True, blank=True, verbose_name='Data Escolhida')
    participants_count = models.PositiveSmallIntegerField(default=1, verbose_name='Nº de Participantes')
    total_price_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total (AOA)')
    special_notes = models.TextField(blank=True, verbose_name='Observações / Restrições')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed', verbose_name='Estado')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva de Tour / Evento'
        verbose_name_plural = 'Reservas de Tours / Eventos'
        ordering = ['-created_at']

    def __str__(self):
        return f"Tour {self.reference_code} — {self.participant_name} ({self.event.title})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            code = f"TR-{uuid.uuid4().hex[:6].upper()}"
            while EventBooking.objects.filter(reference_code=code).exclude(pk=self.pk).exists():
                code = f"TR-{uuid.uuid4().hex[:6].upper()}"
            self.reference_code = code
        if not self.selected_date:
            self.selected_date = self.event.start_date
        unit = 0 if self.event.is_free else float(self.event.price_aoa or 0)
        self.total_price_aoa = unit * (self.participants_count or 1)
        super().save(*args, **kwargs)
