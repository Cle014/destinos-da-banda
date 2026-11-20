from django.contrib import admin
from .models import GalleryItem

@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'item_type', 'category', 'province', 'is_featured', 'created_at')
    list_filter = ('item_type', 'category', 'province', 'is_featured')
    search_fields = ('title', 'location_name', 'description', 'photographer')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured',)
