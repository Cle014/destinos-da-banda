
from django.urls import path
from . import views

app_name = 'core'  # Namespace para usar em templates: {% url 'core:home' %}

urlpatterns = [
    path('', views.home_view, name='home'),
]
