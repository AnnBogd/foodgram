"""Сериализаторы первой версии приложения api."""

import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.db import transaction
from djoser.serializers import UserSerializer, UserCreateSerializer
from rest_framework.serializers import (
    ValidationError,
    ImageField,
    ModelSerializer,
    PrimaryKeyRelatedField,
    SerializerMethodField
)

from recipes.models import (
    Favourite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag
)
from users.models import Subscription

current_user = get_user_model()


class Base64ImageField(ImageField):
    """Класс специализированного поля для изображений."""

    def to_internal_value(self, data):
        """Преобразовать входную строку в файл изображения."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstring = data.split(';base64,')
            extension = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstring),
                name='temp.' + extension
            )
        return super().to_internal_value(data)


class CustomUserSerializer(UserSerializer):
    """Сериализатор для отображения профиля пользователя."""

    is_subscribed = SerializerMethodField()

    class Meta:
        model = current_user
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj: AbstractUser) -> bool:
        """Определить кастомное поле is_subscribed."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return (
            Subscription.objects
            .filter(user=request.user, author=obj)
            .exists()
        )


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания нового пользователя."""

    class Meta:
        model = current_user
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        extra_kwargs = {'password': {'write_only': True}}


class AvatarSerializer(ModelSerializer):
    """Сериализатор для PUT и DELETE запросов по эндпоинту аватара."""

    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = current_user
        fields = ('avatar',)


class TagSerializer(ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(ModelSerializer):
    """Сериализатор модели связи ингредиентов и рецепта."""

    id = PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeReadSerializer(ModelSerializer):
    """Сериализатор рецептов для GET запросов."""

    tags = TagSerializer(many=True)
    author = CustomUserSerializer()
    ingredients = IngredientSerializer(many=True)
    is_favorited = SerializerMethodField()
    is_in_shopping_cart = SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj: Recipe) -> bool:
        """Определить кастомное поле is_favorited."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favourite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj: Recipe) -> bool:
        """Определить кастомное поле is_in_shopping_cart."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return (
            ShoppingCart.objects
            .filter(user=request.user, recipe=obj)
            .exists()
        )


class RecipeWriteSerializer(ModelSerializer):
    """Сериализатор рецептов для запросов на запись."""

    ingredients = IngredientRecipeSerializer(many=True, required=True)
    tags = PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate(self, data: dict) -> dict:
        """Проверить вводимые данные."""
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if not ingredients:
            raise ValidationError(
                {
                    'ingredients':
                    'В рецепте должен быть хотя бы один ингредиент.'
                }
            )
        ingredients_ids = [item['id'].pk for item in ingredients]
        if len(ingredients_ids) != len(set(ingredients_ids)):
            raise ValidationError(
                {'ingredients': 'Ингредиенты в рецепте не должны повторяться.'}
            )
        if not tags:
            raise ValidationError(
                {'tags': 'Нужен хотя бы один тег.'})
        if len(tags) != len(set(tags)):
            raise ValidationError({'tags': 'Теги не должны повторяться.'})
        return data

    def _save_ingredients(self, recipe: Recipe, ingredients: list) -> None:
        """Сохранить ингредиенты в промежуточную таблицу."""
        for ingredient_data in ingredients:
            IngredientRecipe.objects.create(
                recipe_id=recipe.id,
                ingredient_id=ingredient_data['id'].id,
                amount=ingredient_data['amount']
            )

    @transaction.atomic
    def create(self, validated_data: dict) -> Recipe:
        """Создать рецепт и сохранить связи с ингредиентами и тегами."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        author = self.context['request'].user
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance: Recipe, validated_data: dict) -> Recipe:
        """Обновить рецепт."""
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        new_image = validated_data.get('image', None)
        if new_image is not None and instance.image:
            instance.image.delete(save=False)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.ingredients.clear()
            self._save_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance: Recipe) -> dict:
        """Определить сериализатор для выдачи ответа."""
        return RecipeReadSerializer(instance, context=self.context).data

# избранное и список покупок
