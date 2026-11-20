from django.contrib import admin
from .models import Route, RouteStop


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1
    fields = ['day', 'order', 'destination', 'duration_hours', 'notes']
    autocomplete_fields = ['destination']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration_days', 'difficulty', 'status', 'is_featured', 'created_at']
    list_filter = ['status', 'difficulty', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RouteStopInline]
    search_fields = ['name', 'description']
