from django.urls import path
from . import views

app_name = 'destinations'

urlpatterns = [
    path('', views.destination_list, name='list'),
    path('historias/', views.article_list, name='article_list'),
    path('historias/<slug:slug>/', views.article_detail, name='article_detail'),
    path('<slug:slug>/reservar-visita/', views.destination_visit_book, name='visit_book'),
    path('<slug:slug>/', views.destination_detail, name='detail'),
]
