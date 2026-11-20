from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('', views.route_list, name='list'),
    path('planeador/', views.trip_planner_view, name='planner'),
    path('plano/adicionar/', views.plan_add_item, name='plan_add'),
    path('plano/remover/', views.plan_remove_item, name='plan_remove'),
    path('plano/limpar/', views.plan_clear, name='plan_clear'),
    path('plano/checkout/', views.plan_checkout_submit, name='plan_checkout'),
    path('jornada/<str:reference_code>/', views.trip_order_detail, name='order_detail'),
    path('jornada/<str:reference_code>/item/<int:item_id>/substituir/', views.trip_order_replace_item, name='order_replace_item'),
    path('jornada/<str:reference_code>/item/<int:item_id>/cancelar/', views.trip_order_cancel_item, name='order_cancel_item'),
    path('jornada/<str:reference_code>/item/<int:item_id>/simular-estado/', views.trip_order_simulate_item_status, name='order_simulate_item'),
    path('<slug:slug>/', views.route_detail, name='detail'),
]
