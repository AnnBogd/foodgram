"""Кастомные фильтры первой версии приложения api."""

from django.db.models import QuerySet
from django_filters import (
    BooleanFilter,
    FilterSet,
    ModelChoiceFilter,
    ModelMultipleChoiceFilter
)
from django.contrib.auth import get_user_model

from recipes.models import Recipe, Tag

current_user = get_user_model()


class RecipeFilter(FilterSet):
    """Кастомный фильтр для вьюсета рецептов."""

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False
    )
    author = ModelChoiceFilter(queryset=current_user.objects.all())
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_is_favorited(
        self,
        queryset: QuerySet,
        name: str,
        value: int
    ) -> QuerySet:
        """Обработать входное значение и сформировать выборку."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorite__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(
        self,
        queryset: QuerySet,
        name: str,
        value: int
    ) -> QuerySet:
        """Обработать входное значение и сформировать выборку."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset
