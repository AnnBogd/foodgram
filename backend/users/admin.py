"""Конфигурации админ-зоны приложения users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Subscription


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Кастомная конфигурация админ-зоны пользователя."""

    list_display = (
        'id',
        'first_name',
        'last_name',
        'email',
        'username',
        'avatar',
        'password',
    )
    search_fields = ('email', 'username')
    list_display_links = ('email', 'username')
    list_filter = ('email', 'username')


@admin.register(Subscription)
class FollowAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны подписок."""

    list_display = ('id', 'user', 'author')
    list_display_links = ('id', 'user', 'author')
    search_fields = (
        'user__username',
        'user__email',
        'author__username',
        'author__email',
    )
    list_filter = ('user', 'author')
