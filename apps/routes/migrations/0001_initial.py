from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('destinations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Nome da rota')),
                ('slug', models.SlugField(blank=True, max_length=220, unique=True)),
                ('description', models.TextField(verbose_name='Descrição')),
                ('short_description', models.CharField(max_length=300, verbose_name='Descrição curta')),
                ('image', models.ImageField(blank=True, null=True, upload_to='routes/', verbose_name='Imagem de capa')),
                ('duration_days', models.PositiveSmallIntegerField(default=1, verbose_name='Duração (dias)')),
                ('difficulty', models.CharField(choices=[('easy', 'Fácil'), ('moderate', 'Moderado'), ('hard', 'Difícil')], default='easy', max_length=10)),
                ('status', models.CharField(choices=[('draft', 'Rascunho'), ('published', 'Publicado')], default='draft', max_length=10)),
                ('is_featured', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rota',
                'verbose_name_plural': 'Rotas',
                'ordering': ['-is_featured', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RouteStop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.PositiveSmallIntegerField(default=1, verbose_name='Dia')),
                ('order', models.PositiveSmallIntegerField(default=0, verbose_name='Ordem no dia')),
                ('notes', models.TextField(blank=True, verbose_name='Notas do dia')),
                ('duration_hours', models.PositiveSmallIntegerField(default=2, verbose_name='Duração (horas)')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stops', to='routes.route')),
                ('destination', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='route_stops', to='destinations.destination')),
            ],
            options={
                'verbose_name': 'Paragem',
                'verbose_name_plural': 'Paragens',
                'ordering': ['day', 'order'],
                'unique_together': {('route', 'destination')},
            },
        ),
    ]
