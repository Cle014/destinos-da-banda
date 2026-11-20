from django.urls import path
from . import views

app_name = 'accommodations'

urlpatterns = [
    path('', views.accommodation_list, name='list'),
    path('<slug:slug>/', views.accommodation_detail, name='detail'),
    path('<slug:slug>/reservar/', views.accommodation_book, name='book'),
    path('<slug:slug>/avaliar/', views.accommodation_review, name='review'),
]
