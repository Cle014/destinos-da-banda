from django.contrib import admin
from .models import Event

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'activity_type', 'category', 'province', 'start_date', 'is_free', 'price_aoa', 'status', 'is_featured')
    list_filter = ('activity_type', 'category', 'province', 'status', 'is_free', 'is_featured', 'start_date')
    search_fields = ('title', 'location_venue', 'description', 'organizer_name')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured', 'status')
