"""Конфигурации админ-зоны приложения users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from recipes.models import Favourite, ShoppingCart
from .models import CustomUser, Subscription


class FavouriteInline(admin.TabularInline):
    """Класс для управления избранным прямо из карточки пользователя."""
    model = Favourite
    extra = 0
    verbose_name = 'Рецепт в избранном'
    verbose_name_plural = 'Избранные рецепты'

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return super().get_queryset(request).select_related('recipe')


class ShoppingCartInline(admin.TabularInline):
    """Класс для управления списком покупок прямо из карточки пользователя."""
    model = ShoppingCart
    extra = 0
    verbose_name = 'Рецепт в списке покупок'
    verbose_name_plural = 'Список покупок'

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return super().get_queryset(request).select_related('recipe')


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
    inlines = (FavouriteInline, ShoppingCartInline)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return super().get_queryset(request).select_related('user', 'author')
