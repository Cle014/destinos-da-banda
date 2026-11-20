import datetime
import uuid
from django.db import models
from django.utils.text import slugify

class Accommodation(models.Model):
    TYPE_CHOICES = [
        ('hotel', 'Hotel'),
        ('lodge', 'Lodge & Pousada'),
        ('resort', 'Resort'),
        ('apartment', 'Apartamento de Curta Duração'),
        ('house', 'Casa / Vivenda de Curta Duração'),
        ('room', 'Quarto Particular / Alojamento Local'),
        ('residence', 'Residência / Guest House'),
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

    name = models.CharField(max_length=200, verbose_name='Nome do Alojamento')
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    accommodation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='hotel', verbose_name='Tipo de Alojamento')
    province = models.CharField(max_length=30, choices=PROVINCE_CHOICES, verbose_name='Província')
    city = models.CharField(max_length=100, verbose_name='Cidade / Município')
    address = models.CharField(max_length=250, blank=True, verbose_name='Endereço Completo')
    short_description = models.CharField(max_length=300, verbose_name='Descrição Curta')
    description = models.TextField(verbose_name='Descrição Completa')
    
    price_per_night_aoa = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Preço mín. / noite (AOA)')
    price_max_per_night_aoa = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Preço máx. / noite (AOA)')
    price_per_night_usd = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Preço aprox. / noite (USD)')
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Latitude')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Longitude')
    cancellation_policy = models.CharField(
        max_length=280,
        default='Cancelamento gratuito até 48h antes do check-in; reembolso de 50% até 24h antes.',
        verbose_name='Política de Cancelamento'
    )
    is_verified = models.BooleanField(default=True, verbose_name='Alojamento Verificado')
    verification_criteria = models.CharField(
        max_length=250,
        default='NIF, Licença Hoteleira/INFOTUR, contacto telefónico e vistoria presencial validados',
        blank=True,
        verbose_name='Critério de Verificação'
    )
    is_demo = models.BooleanField(default=False, verbose_name='Registo Demo')
    
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=4.5, verbose_name='Classificação')
    review_count = models.PositiveIntegerField(default=12, verbose_name='Número de Avaliações')
    
    max_guests = models.PositiveSmallIntegerField(default=2, verbose_name='Capacidade Máx. Hóspedes')
    bedrooms = models.PositiveSmallIntegerField(default=1, verbose_name='Número de Quartos')
    bathrooms = models.PositiveSmallIntegerField(default=1, verbose_name='Casas de Banho')
    total_units = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='Total de Unidades Disponíveis',
        help_text='Para casas/apartamentos inteiros = 1; para residências sem tipologias = nº de unidades.'
    )
    house_rules = models.TextField(
        blank=True,
        default='Check-in a partir das 14h00; Check-out até às 12h00. Respeitar o silêncio nocturno após as 22h00.',
        verbose_name='Regras do Alojamento'
    )
    booking_conditions = models.TextField(
        blank=True,
        default='Apresentação de documento de identificação no check-in. Pagamento em Kwanzas via Multicaixa Express, Referência ou TPA.',
        verbose_name='Condições de Reserva'
    )
    
    amenities = models.JSONField(default=list, blank=True, help_text='Lista de comodidades ex: ["wifi", "ac", "pool", "breakfast", "parking"]')
    
    image = models.ImageField(upload_to='accommodations/', blank=True, null=True, verbose_name='Foto Principal')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Foto (externa)')
    
    contact_phone = models.CharField(max_length=30, blank=True, verbose_name='Telefone')
    contact_whatsapp = models.CharField(max_length=30, blank=True, verbose_name='WhatsApp')
    contact_email = models.EmailField(blank=True, verbose_name='Email de Reservas')
    
    is_featured = models.BooleanField(default=False, verbose_name='Alojamento em Destaque')
    is_active = models.BooleanField(default=True, verbose_name='Activo para Reservas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alojamento'
        verbose_name_plural = 'Alojamentos'
        ordering = ['-is_featured', '-rating', 'price_per_night_aoa']

    def __str__(self):
        return f"{self.name} ({self.get_accommodation_type_display()}) — {self.get_province_display()}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'alojamento'
            slug = base
            counter = 1
            while Accommodation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
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
        return 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=1200&q=80'

    @property
    def formatted_price_aoa(self):
        return f"{self.price_per_night_aoa:,.0f} Kz".replace(',', ' ')

    @property
    def formatted_price_range_aoa(self):
        min_p = float(self.price_per_night_aoa or 0)
        max_p = float(self.price_max_per_night_aoa or 0)
        if max_p > min_p:
            return f"{min_p:,.0f} Kz – {max_p:,.0f} Kz".replace(',', ' ')
        return f"{min_p:,.0f} Kz".replace(',', ' ')


    @property
    def is_hotel_model(self):
        return self.accommodation_type in ('hotel', 'lodge', 'resort') or self.room_types.exists()

    def get_available_units_for_period(self, check_in=None, check_out=None):
        """
        Calcula a disponibilidade real do alojamento para o intervalo [check_in, check_out).
        - Se tiver tipologias (RoomType), soma as unidades disponíveis das tipologias activas.
        - Se for alojamento de curta duração (casa/apartamento/quarto único), verifica conflitos de datas
          dia a dia contra self.total_units.
        """
        active_types = list(self.room_types.filter(is_active=True))
        if active_types:
            return sum(rt.get_available_units(check_in, check_out) for rt in active_types)

        total = max(1, self.total_units or 1)
        if not check_in or not check_out or check_out <= check_in:
            return total

        overlapping = list(
            self.bookings.filter(
                status__in=['pending', 'confirmed'],
                check_in__lt=check_out,
                check_out__gt=check_in,
            )
        )
        if not overlapping:
            return total

        days = min(365, (check_out - check_in).days)
        max_occupied = 0
        for offset in range(days):
            day = check_in + datetime.timedelta(days=offset)
            occ = sum(
                (b.units_reserved or 1)
                for b in overlapping
                if b.check_in <= day < b.check_out
            )
            if occ > max_occupied:
                max_occupied = occ
        return max(0, total - max_occupied)


class AccommodationImage(models.Model):
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='gallery_photos')
    image = models.ImageField(upload_to='accommodations/gallery/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True)
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Foto do Alojamento'
        verbose_name_plural = 'Fotos do Alojamento'
        ordering = ['order']


class RoomType(models.Model):
    """
    Tipologia de Quarto ou Suite para Hotéis, Lodges e Resorts.
    Gere capacidade, camas, preço, total de unidades físicas e disponibilidade real por período.
    """
    CATEGORY_CHOICES = [
        ('single', 'Quarto Single / Individual'),
        ('standard', 'Quarto Standard'),
        ('double', 'Quarto Duplo (Casal)'),
        ('twin', 'Quarto Twin (2 Camas)'),
        ('superior', 'Quarto Superior / Deluxe'),
        ('suite', 'Suite Executiva / Presidencial'),
        ('bungalow', 'Bungalow / Chalet Privativo'),
        ('family', 'Quarto Familiar'),
    ]

    accommodation = models.ForeignKey(
        Accommodation,
        on_delete=models.CASCADE,
        related_name='room_types',
        verbose_name='Estabelecimento Hoteleiro'
    )
    name = models.CharField(max_length=150, verbose_name='Nome da Tipologia')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='standard', verbose_name='Tipologia')
    description = models.TextField(blank=True, verbose_name='Descrição do Quarto / Suite')
    capacity_guests = models.PositiveSmallIntegerField(default=2, verbose_name='Capacidade (Hóspedes)')
    beds_count = models.PositiveSmallIntegerField(default=1, verbose_name='Nº de Camas')
    bed_configuration = models.CharField(max_length=100, default='1 Cama Queen-Size', verbose_name='Configuração de Camas')
    amenities = models.JSONField(default=list, blank=True, verbose_name='Comodidades do Quarto')
    price_per_night_aoa = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Preço / Noite (AOA)')
    total_units = models.PositiveSmallIntegerField(default=5, verbose_name='Nº Total de Unidades desta Tipologia')
    booking_conditions = models.CharField(
        max_length=250,
        blank=True,
        default='Pequeno-almoço incluído · Cancelamento gratuito até 48h antes',
        verbose_name='Condições de Reserva'
    )
    image = models.ImageField(upload_to='accommodations/rooms/', blank=True, null=True, verbose_name='Fotografia')
    image_url = models.URLField(max_length=500, blank=True, verbose_name='URL da Fotografia')
    is_active = models.BooleanField(default=True, verbose_name='Activa para Reserva')

    class Meta:
        verbose_name = 'Tipologia de Quarto / Suite'
        verbose_name_plural = 'Tipologias de Quartos & Suites'
        ordering = ['price_per_night_aoa', 'id']

    def __str__(self):
        return f"{self.name} — {self.accommodation.name} ({self.formatted_price_aoa}/noite)"

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return self.accommodation.display_image

    @property
    def formatted_price_aoa(self):
        return f"{self.price_per_night_aoa:,.0f} Kz".replace(',', ' ')

    def get_available_units(self, check_in=None, check_out=None, exclude_booking_pk=None):
        """
        Calcula o número exacto de unidades disponíveis desta tipologia no intervalo [check_in, check_out).
        Analisa a ocupação noite a noite entre check_in e check_out considerando reservas 'pending' e 'confirmed'.
        Reservas 'cancelled' libertam imediatamente o inventário.
        """
        total = max(0, self.total_units or 0)
        if not self.is_active or total == 0:
            return 0
        if not check_in or not check_out or check_out <= check_in:
            return total

        qs = self.bookings.filter(
            status__in=['pending', 'confirmed'],
            check_in__lt=check_out,
            check_out__gt=check_in,
        )
        if exclude_booking_pk:
            qs = qs.exclude(pk=exclude_booking_pk)
        overlapping = list(qs)
        if not overlapping:
            return total

        days = min(365, (check_out - check_in).days)
        max_occupied = 0
        for offset in range(days):
            day = check_in + datetime.timedelta(days=offset)
            occ = sum(
                (b.units_reserved or 1)
                for b in overlapping
                if b.check_in <= day < b.check_out
            )
            if occ > max_occupied:
                max_occupied = occ
        return max(0, total - max_occupied)


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendente de Confirmação'),
        ('confirmed', 'Confirmada'),
        ('completed', 'Concluída'),
        ('cancelled', 'Cancelada'),
    ]

    reference_code = models.CharField(max_length=20, unique=True, editable=False, verbose_name='Código de Reserva')
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='bookings', verbose_name='Alojamento')
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name='Tipologia de Quarto / Suite'
    )
    units_reserved = models.PositiveSmallIntegerField(default=1, verbose_name='Nº de Unidades / Quartos')
    
    guest_name = models.CharField(max_length=150, verbose_name='Nome do Hóspede')
    guest_email = models.EmailField(verbose_name='Email de Contacto')
    guest_phone = models.CharField(max_length=30, verbose_name='Telefone / WhatsApp')
    
    check_in = models.DateField(verbose_name='Data de Entrada')
    check_out = models.DateField(verbose_name='Data de Saída')
    guests_count = models.PositiveSmallIntegerField(default=1, verbose_name='Número de Hóspedes')
    
    total_nights = models.PositiveSmallIntegerField(default=1, verbose_name='Total de Noites')
    total_price_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Valor Total (AOA)')
    
    special_requests = models.TextField(blank=True, verbose_name='Observações / Pedidos Especiais')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado da Reserva')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reserva {self.reference_code} — {self.guest_name} ({self.accommodation.name})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            code = f"DB-{uuid.uuid4().hex[:6].upper()}"
            while Booking.objects.filter(reference_code=code).exclude(pk=self.pk).exists():
                code = f"DB-{uuid.uuid4().hex[:6].upper()}"
            self.reference_code = code
        if self.check_in and self.check_out and self.check_out > self.check_in:
            self.total_nights = (self.check_out - self.check_in).days
            nightly_rate = self.room_type.price_per_night_aoa if self.room_type else self.accommodation.price_per_night_aoa
            self.total_price_aoa = self.total_nights * nightly_rate * max(1, self.units_reserved or 1)
        super().save(*args, **kwargs)


class AccommodationReview(models.Model):
    """Avaliação de alojamento restrita a reservas concluídas."""
    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name='reviews', verbose_name='Alojamento')
    booking_reference = models.CharField(max_length=24, verbose_name='Código da Reserva Concluída')
    guest_name = models.CharField(max_length=150, verbose_name='Nome do Hóspede')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Classificação (1-5)')
    comment = models.TextField(verbose_name='Comentário')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação de Alojamento'
        verbose_name_plural = 'Avaliações de Alojamento'
        ordering = ['-created_at']
        unique_together = [['accommodation', 'booking_reference']]

    def __str__(self):
        return f"{self.guest_name} ({self.booking_reference}) → {self.accommodation.name} ({self.rating}★)"


class TripOrder(models.Model):
    """
    Reserva única multi-parceiro para uma jornada integrada
    (Alojamentos + Guias + Eventos/Actividades).
    """
    STATUS_CHOICES = [
        ('pending', 'Pendente de Confirmação dos Parceiros'),
        ('confirmed', 'Confirmada'),
        ('partial_failure', 'Atenção: Falha Parcial (Alternativas Disponíveis)'),
        ('completed', 'Viagem Concluída'),
        ('cancelled', 'Cancelada'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mcx_express', 'Multicaixa Express (Telemóvel)'),
        ('referencia_mcx', 'Pagamento por Referência Multicaixa'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('awaiting', 'Aguarda Pagamento / Pré-Autorização'),
        ('paid', 'Pago / Garantido'),
        ('refunded_partial', 'Ajustado por Alteração de Item'),
    ]

    reference_code = models.CharField(max_length=20, unique=True, editable=False, verbose_name='Código da Jornada')
    province = models.CharField(max_length=30, default='huambo', verbose_name='Província')
    guest_name = models.CharField(max_length=150, verbose_name='Nome do Viajante')
    guest_email = models.EmailField(verbose_name='Email')
    guest_phone = models.CharField(max_length=30, verbose_name='Telefone / WhatsApp')
    start_date = models.DateField(verbose_name='Data de Início')
    end_date = models.DateField(verbose_name='Data de Fim')
    travelers_count = models.PositiveSmallIntegerField(default=2, verbose_name='Nº de Viajantes')

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mcx_express', verbose_name='Método de Pagamento Local')
    payment_phone = models.CharField(max_length=30, blank=True, verbose_name='Nº Multicaixa Express')
    payment_entity = models.CharField(max_length=10, default='00542', verbose_name='Entidade Multicaixa')
    payment_reference = models.CharField(max_length=20, blank=True, verbose_name='Referência Multicaixa')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='paid', verbose_name='Estado do Pagamento')

    total_aoa = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Total da Reserva (Kz)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado Global')
    notes = models.TextField(blank=True, verbose_name='Notas da Viagem')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reserva Única (Jornada)'
        verbose_name_plural = 'Reservas Únicas (Jornadas)'
        ordering = ['-created_at']

    def __str__(self):
        return f"Jornada {self.reference_code} — {self.guest_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            code = f"DB-{uuid.uuid4().hex[:6].upper()}"
            while TripOrder.objects.filter(reference_code=code).exclude(pk=self.pk).exists():
                code = f"DB-{uuid.uuid4().hex[:6].upper()}"
            self.reference_code = code
        if not self.payment_reference:
            num = str(uuid.uuid4().int)[:9]
            self.payment_reference = f"{num[:3]} {num[3:6]} {num[6:9]}"
        super().save(*args, **kwargs)

    def recalculate_state(self):
        items = list(self.items.all())
        active_items = [i for i in items if i.status != 'cancelled']
        self.total_aoa = sum((i.subtotal_aoa for i in active_items if i.status != 'declined'), 0)

        if not active_items:
            self.status = 'cancelled'
        elif any(i.status == 'declined' for i in active_items):
            self.status = 'partial_failure'
        elif all(i.status == 'completed' for i in active_items):
            self.status = 'completed'
        elif all(i.status in ('confirmed', 'completed') for i in active_items):
            self.status = 'confirmed'
        else:
            self.status = 'pending'
        self.save(update_fields=['total_aoa', 'status', 'updated_at'])

    @property
    def formatted_total_aoa(self):
        return f"{self.total_aoa:,.0f} Kz".replace(',', ' ')


class TripOrderItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('accommodation', 'Alojamento'),
        ('guide', 'Guia Turístico'),
        ('event', 'Actividade / Evento'),
        ('destination', 'Visita / Entrada em Destino'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('confirmed', 'Confirmado'),
        ('declined', 'Recusado pelo Parceiro'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado'),
    ]

    order = models.ForeignKey(TripOrder, on_delete=models.CASCADE, related_name='items', verbose_name='Reserva')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, verbose_name='Tipo de Parceiro')
    item_id = models.PositiveIntegerField(verbose_name='ID do Registo')
    item_slug = models.SlugField(max_length=220, blank=True)
    title = models.CharField(max_length=200, verbose_name='Item / Parceiro')
    partner_name = models.CharField(max_length=200, blank=True, verbose_name='Entidade Parceira')
    day_number = models.PositiveSmallIntegerField(default=1, verbose_name='Dia do Itinerário')
    unit_price_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Preço Unitário (Kz)')
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name='Qtd / Noites / Dias')
    subtotal_aoa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Subtotal (Kz)')
    cancellation_policy = models.CharField(
        max_length=280,
        default='Cancelamento gratuito até 48h antes; reembolso de 50% até 24h.',
        verbose_name='Política de Cancelamento'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Estado do Item')
    decline_reason = models.CharField(max_length=250, blank=True, verbose_name='Motivo de Recusa / Indisponibilidade')
    replaced_by_title = models.CharField(max_length=200, blank=True, verbose_name='Substituído por')

    class Meta:
        verbose_name = 'Item da Reserva Única'
        verbose_name_plural = 'Itens da Reserva Única'
        ordering = ['day_number', 'id']

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        self.subtotal_aoa = (self.unit_price_aoa or 0) * (self.quantity or 1)
        super().save(*args, **kwargs)

    @property
    def formatted_unit_price_aoa(self):
        return f"{self.unit_price_aoa:,.0f} Kz".replace(',', ' ')

    @property
    def formatted_subtotal_aoa(self):
        return f"{self.subtotal_aoa:,.0f} Kz".replace(',', ' ')
