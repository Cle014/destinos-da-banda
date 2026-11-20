from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),

    # Edição unificada de qualquer registo
    path('editar/<str:model_key>/<int:pk>/', views.record_edit, name='record_edit'),

    # Destinos & Categorias
    path('destinos/adicionar/', views.destination_add, name='destination_add'),
    path('destinos/<int:pk>/eliminar/', views.destination_delete, name='destination_delete'),
    path('destinos/<int:pk>/alternar/', views.destination_toggle, name='destination_toggle'),
    path('categorias/adicionar/', views.category_add, name='category_add'),
    path('categorias/<int:pk>/eliminar/', views.category_delete, name='category_delete'),

    # Galeria
    path('galeria/adicionar/', views.gallery_add, name='gallery_add'),
    path('galeria/<int:pk>/eliminar/', views.gallery_delete, name='gallery_delete'),
    path('galeria/<int:pk>/alternar/', views.gallery_toggle, name='gallery_toggle'),

    # Rotas & Paragens
    path('rotas/adicionar/', views.route_add, name='route_add'),
    path('rotas/<int:pk>/eliminar/', views.route_delete, name='route_delete'),
    path('rotas/<int:pk>/alternar/', views.route_toggle, name='route_toggle'),
    path('rotas/paragens/adicionar/', views.route_stop_add, name='route_stop_add'),
    path('rotas/paragens/<int:pk>/eliminar/', views.route_stop_delete, name='route_stop_delete'),

    # Alojamentos
    path('alojamentos/adicionar/', views.accommodation_add, name='accommodation_add'),
    path('alojamentos/<int:pk>/eliminar/', views.accommodation_delete, name='accommodation_delete'),
    path('alojamentos/<int:pk>/alternar/', views.accommodation_toggle, name='accommodation_toggle'),

    # Reservas de Alojamento
    path('reservas/adicionar/', views.booking_add, name='booking_add'),
    path('reservas/<int:pk>/status/', views.booking_update_status, name='booking_update_status'),
    path('reservas/<int:pk>/eliminar/', views.booking_delete, name='booking_delete'),

    # Eventos
    path('eventos/adicionar/', views.event_add, name='event_add'),
    path('eventos/<int:pk>/eliminar/', views.event_delete, name='event_delete'),
    path('eventos/<int:pk>/alternar/', views.event_toggle, name='event_toggle'),

    # Guias Turísticos & Especialidades
    path('guias/adicionar/', views.guide_add, name='guide_add'),
    path('guias/<int:pk>/eliminar/', views.guide_delete, name='guide_delete'),
    path('guias/<int:pk>/alternar/', views.guide_toggle, name='guide_toggle'),
    path('guias/especialidades/adicionar/', views.specialty_add, name='specialty_add'),
    path('guias/especialidades/<int:pk>/eliminar/', views.specialty_delete, name='specialty_delete'),

    # Tipologias de Quartos & Suites
    path('alojamentos/tipologias/adicionar/', views.room_type_add, name='room_type_add'),
    path('alojamentos/tipologias/<int:pk>/eliminar/', views.room_type_delete, name='room_type_delete'),
    path('alojamentos/tipologias/<int:pk>/alternar/', views.room_type_toggle, name='room_type_toggle'),

    # Blog Cultural
    path('artigos/adicionar/', views.article_add, name='article_add'),
    path('artigos/<int:pk>/eliminar/', views.article_delete, name='article_delete'),
    path('artigos/<int:pk>/alternar/', views.article_toggle, name='article_toggle'),

    # Reservas de Tours, Visitas e Jornadas Multi-Parceiro
    path('reservas-tours/adicionar/', views.tour_booking_add, name='tour_booking_add'),
    path('reservas-tours/<int:pk>/status/', views.tour_booking_update_status, name='tour_booking_update_status'),
    path('reservas-tours/<int:pk>/eliminar/', views.tour_booking_delete, name='tour_booking_delete'),
    path('reservas-visitas/adicionar/', views.visit_booking_add, name='visit_booking_add'),
    path('reservas-visitas/<int:pk>/status/', views.visit_booking_update_status, name='visit_booking_update_status'),
    path('reservas-visitas/<int:pk>/eliminar/', views.visit_booking_delete, name='visit_booking_delete'),
    path('jornadas/adicionar/', views.trip_order_add, name='trip_order_add'),
    path('jornadas/<int:pk>/status/', views.trip_order_update_status, name='trip_order_update_status'),
    path('jornadas/<int:pk>/eliminar/', views.trip_order_delete, name='trip_order_delete'),
]
