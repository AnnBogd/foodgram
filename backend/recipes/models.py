"""Модели приложения recipes."""

import secrets

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from .constants import (
    MAX_NAME_LENGTH,
    MIN_COOKING_TIME,
    MIN_INGREDIENT_AMOUNT
)


def generate_short_code() -> str:
    """Сгенерировать короткий код для ссылки."""
    return secrets.token_urlsafe(4)[:6]


class IngredientRecipe(models.Model):
    """Промежуточная модель для связи рецептов и ингредиентов."""

    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        'Ingredient',
        on_delete=models.CASCADE,
        related_name='recipe_list',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=[
            MinValueValidator(
                MIN_INGREDIENT_AMOUNT,
                'Количество ингредиента не может быть меньше '
                f'{MIN_INGREDIENT_AMOUNT}'
            )
        ],
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self) -> str:
        """Переопределить строковое представление связи."""
        return (f'{self.ingredient.name} — {self.amount} '
                f'{self.ingredient.measurement_unit}')


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(
        'Название тега',
        max_length=MAX_NAME_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        'Слаг тега',
        unique=True,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self) -> str:
        """Переопределить строковое определение тега."""
        return f'{self.name}'


class Ingredient(models.Model):
    """Модель ингредиента."""

    name = models.CharField(
        'Название ингредиента',
        max_length=MAX_NAME_LENGTH,
    )
    measurement_unit = models.CharField(
        'Единица измерения ингредиента',
        max_length=MAX_NAME_LENGTH,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self) -> str:
        """Переопределить строковое определение ингредиента."""
        return f'{self.name}'


class Recipe(models.Model):
    """Модель рецепта."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        'Название рецепта',
        max_length=MAX_NAME_LENGTH,
    )
    image = models.ImageField(
        'Фото рецепта',
        upload_to='recipes/images/',
    )
    text = models.TextField()
    ingredients = models.ManyToManyField(
        Ingredient,
        through=IngredientRecipe,
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления в минутах',
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                'Время приготовления не может быть меньше '
                f'{MIN_COOKING_TIME} минут'
            )
        ]
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации рецепта',
    )
    short_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True,
        verbose_name='Короткий код',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)
        default_related_name = 'recipes'

    def __str__(self) -> str:
        """Переопределить строковое определение рецепта."""
        return f'{self.name}'

    def save(self, *args, **kwargs) -> None:
        """Сохранить короткий код в объект рецепта."""
        if not self.short_code:
            self.short_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self) -> str:
        """Сгенерировать уникальный короткий код."""
        while True:
            code = generate_short_code()
            if not Recipe.objects.filter(short_code=code).exists():
                return code


class Favourite(models.Model):
    """Модель связи рецепта и пользователя через избранное."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        default_related_name = 'favourite'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_favourite'
            )
        ]

    def __str__(self):
        """Переопределить строковое представление избранного."""
        return f'{self.user.username} добавил "{self.recipe.name}" в избранное'


class ShoppingCart(models.Model):
    """Модель связи рецептов и пользователя через список покупок."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        default_related_name = 'shopping_cart'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_shopping_cart'
            )
        ]

    def __str__(self):
        """Переопределить строковое представление списка покупок."""
        return (f'{self.user.username} добавил "{self.recipe.name}" '
                'в список покупок.')
