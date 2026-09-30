"""Кастомные фильтры первой версии приложения api."""

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django_filters import (CharFilter, FilterSet, ModelChoiceFilter,
                            ModelMultipleChoiceFilter, NumberFilter)
from recipes.models import Ingredient, Recipe, Tag

current_user = get_user_model()


class IngredientFilter(FilterSet):
    """Кастомный фильтр для вьюсета ингредиентов."""

    name = CharFilter(method='filter_by_name')

    class Meta:
        model = Ingredient
        fields = ('name',)

    def filter_by_name(
        self,
        queryset: QuerySet,
        name: str,
        value: int
    ) -> QuerySet:
        """Обработать входное значение и сформировать выборку."""
        if not value:
            return queryset
        return queryset.filter(
            Q(name__istartswith=value) | Q(name__icontains=value)
        ).annotate(
            search_order=Case(
                When(name__istartswith=value, then=Value(1)),
                When(name__icontains=value, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        ).order_by('search_order', 'name')


class RecipeFilter(FilterSet):
    """Кастомный фильтр для вьюсета рецептов."""

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        conjoined=False
    )
    author = ModelChoiceFilter(queryset=current_user.objects.all())
    is_favorited = NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(method='filter_is_in_shopping_cart')

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
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favourite__user=user)
        return queryset

    def filter_is_in_shopping_cart(
        self,
        queryset: QuerySet,
        name: str,
        value: int
    ) -> QuerySet:
        """Обработать входное значение и сформировать выборку."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        return queryset
