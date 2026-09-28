"""Сериализаторы первой версии приложения api."""

import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.constants import MIN_COOKING_TIME
from recipes.models import (Favourite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework.serializers import (ImageField, ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField, ValidationError)
from users.models import Subscription

current_user = get_user_model()


class Base64ImageField(ImageField):
    """Класс специализированного поля для изображений."""

    def to_internal_value(self, data: str) -> UploadedFile:
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

    def __init__(self, *args, **kwargs):
        """Определить параметры поля в зависимости от запроса."""
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'PUT':
            self.fields['avatar'].required = True
            self.fields['avatar'].allow_null = False

    def update(
            self,
            instance: AbstractUser,
            validated_data: dict
    ) -> AbstractUser:
        """Удалить старый аватар перед сохранением нового."""
        if instance.avatar:
            instance.avatar.delete(save=False)
        return super().update(instance, validated_data)


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
    ingredients = SerializerMethodField()
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

    def get_ingredients(self, obj: Recipe) -> list:
        """Получить список ингредиентов для текущего рецепта."""
        recipe_ingredients = obj.ingredient_list.all()
        return [
            {
                'id': item.ingredient.id,
                'name': item.ingredient.name,
                'measurement_unit': item.ingredient.measurement_unit,
                'amount': item.amount
            }
            for item in recipe_ingredients
        ]

    def get_is_favorited(self, obj: Recipe) -> bool:
        """Определить кастомное поле is_favorited."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.favourite.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj: Recipe) -> bool:
        """Определить кастомное поле is_in_shopping_cart."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.shopping_cart.filter(user=request.user).exists()


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
        extra_kwargs = {
            'cooking_time': {'min_value': MIN_COOKING_TIME},
        }

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
                ingredient_id=ingredient_data['id'].pk,
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
        """Преобразовать данные для выдачи ответа."""
        return RecipeReadSerializer(instance, context=self.context).data


class ShortRecipeSerializer(ModelSerializer):
    """Сериализатор для краткого отображения рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('__all__',)


class ShoppingCartCreateSerializer(ModelSerializer):
    """Сериализатор для добавления рецепта в список покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, data: dict) -> dict:
        """Проверить введенные данные."""
        user = data.get('user')
        recipe = data.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError('Этот рецепт уже добавлен в список покупок.')
        return data

    def to_representation(self, instance: ShoppingCart) -> dict:
        """Преобразовать данные для выдачи ответа."""
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class FavouriteCreateSerializer(ModelSerializer):
    """Сериализатор для добавления рецепта в избранное."""

    class Meta:
        model = Favourite
        fields = ('user', 'recipe')

    def validate(self, data: dict) -> dict:
        """Проверить введенные данные."""
        user = data.get('user')
        recipe = data.get('recipe')
        if Favourite.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError('Этот рецепт уже добавлен в избранное.')
        return data

    def to_representation(self, instance: Favourite) -> dict:
        """Преобразовать данные для выдачи ответа."""
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class SubscriptionSerializer(CustomUserSerializer):
    """Сериализатор подписок. Наследование от сериализатора юзера."""

    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = (
            CustomUserSerializer.Meta.fields + ('recipes', 'recipes_count'))

    def get_recipes(self, obj: AbstractUser) -> dict:
        """Получить список рецептов автора с учетом лимита."""
        request = self.context.get('request')
        recipes = obj.recipes.all()
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
            if recipes_limit and recipes_limit.isdigit():
                recipes = recipes[:int(recipes_limit)]
        return ShortRecipeSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj: AbstractUser) -> int:
        """Посчитать общее количество рецептов автора."""
        return obj.recipes.count()
