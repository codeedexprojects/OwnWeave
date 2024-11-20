from django.contrib import admin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'name', 'is_favorite', 'is_staff')
    search_fields = ('mobile_number', 'name')
    list_filter = ('is_favorite', 'is_staff')
