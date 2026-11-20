from django.contrib import admin
from .models import Accommodation, AccommodationImage, Booking

class AccommodationImageInline(admin.TabularInline):
    model = AccommodationImage
    extra = 2

@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ('name', 'accommodation_type', 'province', 'city', 'price_per_night_aoa', 'rating', 'is_featured', 'is_active')
    list_filter = ('accommodation_type', 'province', 'is_featured', 'is_active')
    search_fields = ('name', 'city', 'address', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AccommodationImageInline]

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'accommodation', 'guest_name', 'check_in', 'check_out', 'total_nights', 'total_price_aoa', 'status', 'created_at')
    list_filter = ('status', 'check_in', 'created_at')
    search_fields = ('reference_code', 'guest_name', 'guest_email', 'guest_phone')
    readonly_fields = ('reference_code', 'total_nights', 'total_price_aoa', 'created_at')
