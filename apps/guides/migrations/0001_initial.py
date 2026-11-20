from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('destinations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Especialidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=120, unique=True)),
                ('icon', models.CharField(default='fas fa-star', max_length=60)),
                ('color', models.CharField(default='#2D6A4F', max_length=7)),
            ],
            options={'verbose_name': 'Especialidade', 'verbose_name_plural': 'Especialidades', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='GuiaTuristico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, max_length=220, unique=True)),
                ('foto', models.ImageField(blank=True, null=True, upload_to='guides/')),
                ('biografia', models.TextField()),
                ('provincia', models.CharField(max_length=30, choices=[
                    ('bengo','Bengo'),('benguela','Benguela'),('bie','Bié'),
                    ('cabinda','Cabinda'),('cuando_cubango','Cuando Cubango'),
                    ('cuanza_norte','Cuanza Norte'),('cuanza_sul','Cuanza Sul'),
                    ('cunene','Cunene'),('huambo','Huambo'),('huila','Huíla'),
                    ('luanda','Luanda'),('lunda_norte','Lunda Norte'),
                    ('lunda_sul','Lunda Sul'),('malanje','Malanje'),
                    ('moxico','Moxico'),('namibe','Namibe'),('uge','Uíge'),('zaire','Zaíre'),
                ])),
                ('municipio', models.CharField(blank=True, max_length=100)),
                ('anos_experiencia', models.PositiveSmallIntegerField(default=1)),
                ('idiomas', models.JSONField(default=list)),
                ('telefone', models.CharField(blank=True, max_length=30)),
                ('whatsapp', models.CharField(blank=True, max_length=30)),
                ('email', models.EmailField(blank=True)),
                ('instagram', models.URLField(blank=True)),
                ('facebook', models.URLField(blank=True)),
                ('certificacoes', models.TextField(blank=True)),
                ('preco_medio', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('avaliacao_media', models.DecimalField(decimal_places=2, default=0.0, max_digits=3)),
                ('total_avaliacoes', models.PositiveIntegerField(default=0)),
                ('verificado', models.BooleanField(default=False)),
                ('activo', models.BooleanField(default=True)),
                ('destaque', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('especialidades', models.ManyToManyField(blank=True, related_name='guias', to='guides.especialidade')),
                ('destinos', models.ManyToManyField(blank=True, related_name='guias', to='destinations.destination')),
            ],
            options={'verbose_name': 'Guia Turístico', 'verbose_name_plural': 'Guias Turísticos',
                     'ordering': ['-destaque', '-avaliacao_media', '-anos_experiencia']},
        ),
        migrations.CreateModel(
            name='AvaliacaoGuia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('classificacao', models.PositiveSmallIntegerField(validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)])),
                ('pontualidade', models.PositiveSmallIntegerField(default=5, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)])),
                ('simpatia', models.PositiveSmallIntegerField(default=5, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)])),
                ('conhecimento', models.PositiveSmallIntegerField(default=5, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)])),
                ('organizacao', models.PositiveSmallIntegerField(default=5, validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5)])),
                ('comentario', models.TextField(blank=True)),
                ('data', models.DateTimeField(auto_now_add=True)),
                ('guia', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='avaliacoes', to='guides.guiaturistico')),
                ('utilizador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                  related_name='avaliacoes_guias',
                                                  to='auth.user')),
            ],
            options={'verbose_name': 'Avaliação', 'verbose_name_plural': 'Avaliações',
                     'ordering': ['-data'], 'unique_together': {('guia', 'utilizador')}},
        ),
    ]
