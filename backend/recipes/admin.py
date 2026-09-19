"""Конфигурации админ-зоны приложения users."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import (
    Favourite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag
)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны рецептов."""

    list_display = ('author', 'name', 'get_favourite_count')
    search_fields = ('author__username', 'name')
    list_filter = ('tags',)
    readonly_fields = ('get_favourite_count',)

    @admin.display(description='Добавлений в избранное')
    def get_favourite_count(self, obj):
        """Подсчитать количество добавлений рецепта в избранное."""
        return obj.favourite.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return (
            super().get_queryset(request)
            .select_related('author')
            .prefetch_related('tags', 'favourite')
        )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны ингредиентов."""

    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны тегов."""

    list_display = ('id', 'name', 'slug')
    list_filter = ('slug',)
    search_fields = ('slug',)


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны избранного."""

    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return super().get_queryset(request).select_related('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны списка покупок."""

    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Переопределить queryset - добавить связи в запрос."""
        return super().get_queryset(request).select_related('user', 'recipe')


@admin.register(IngredientRecipe)
class IngredientRecipeCartAdmin(admin.ModelAdmin):
    """Кастомная конфигурация админ-зоны промежуточной модели связи."""

    list_display = ('id', 'recipe', 'ingredient', 'amount')
    search_fields = ('recipe', 'ingredient')
