"""Сериализаторы первой версии приложения api."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.db import transaction
from django.db.models import Model
from drf_extra_fields.fields import Base64ImageField
from rest_framework.serializers import (ModelSerializer,
                                        PrimaryKeyRelatedField, ReadOnlyField,
                                        SerializerMethodField, ValidationError)

from recipes.models import (Favourite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import Subscription

current_user = get_user_model()


class UserSerializer(ModelSerializer):
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
        return bool(
            request is not None
            and request.user.is_authenticated
            and (
                Subscription.objects
                .filter(user=request.user, author=obj)
                .exists()
            )
        )


class AvatarSerializer(ModelSerializer):
    """Сериализатор для PUT и DELETE запросов по эндпоинту аватара."""

    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = current_user
        fields = ('avatar',)

    def update(
            self,
            instance: AbstractUser,
            validated_data: dict
    ) -> AbstractUser:
        """Удалить старый аватар с диска перед сохранением нового."""
        if instance.avatar:
            instance.avatar.delete(save=False)
        return super().update(instance, validated_data)


class TagSerializer(ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientReadSerializer(ModelSerializer):
    """Сериализатор для самостоятельного чтения ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInsideRecipeSerializer(ModelSerializer):
    """Сериализатор для чтения ингредиентов внутри рецептов."""

    id = ReadOnlyField(source='ingredient.id')
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientRecipeWriteSerializer(ModelSerializer):
    """Сериализатор для записи ингредиентов в рецепт при его создании."""

    id = PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class RecipeReadSerializer(ModelSerializer):
    """Сериализатор рецептов для GET запросов (для чтения)."""

    tags = TagSerializer(many=True)
    author = UserSerializer()
    ingredients = IngredientInsideRecipeSerializer(
        many=True,
        source='ingredient_list'
    )
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
        return bool(
            request is not None
            and request.user.is_authenticated
            and obj.favourite.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, obj: Recipe) -> bool:
        """Определить кастомное поле is_in_shopping_cart."""
        request = self.context.get('request')
        return bool(
            request is not None
            and request.user.is_authenticated
            and obj.shopping_cart.filter(user=request.user).exists()
        )


class RecipeWriteSerializer(ModelSerializer):
    """Сериализатор рецептов для запросов на запись."""

    ingredients = IngredientRecipeWriteSerializer(many=True, required=True)
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
        image = data.get('image')
        if not image:
            raise ValidationError({'image': 'Изображение обязательно.'})
        if not ingredients:
            raise ValidationError(
                {
                    'ingredients':
                    'В рецепте должен быть хотя бы один ингредиент.'
                }
            )
        ingredients_ids = [item['ingredient'].pk for item in ingredients]
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
                ingredient=ingredient_data['ingredient'],
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
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
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


class AuthorSerializer(UserSerializer):
    """Сериализатор авторов подписки. Наследование от сериализатора юзера."""

    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = (
            UserSerializer.Meta.fields + ('recipes', 'recipes_count'))

    def get_recipes(self, obj: AbstractUser) -> dict:
        """Получить список рецептов автора с учетом лимита."""
        request = self.context.get('request')
        recipes = obj.recipes.all()
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
            if (
                recipes_limit
                and recipes_limit.isdigit()
                and int(recipes_limit) > 0
            ):
                recipes = recipes[:int(recipes_limit)]
        return ShortRecipeSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj: AbstractUser) -> int:
        """Посчитать общее количество рецептов автора."""
        return obj.recipes.count()


class SubscriptionSerializer(ModelSerializer):
    """Сериализатор подписки."""

    class Meta:
        model = Subscription
        fields = ('user', 'author')
        read_only_fields = ('user',)

    def validate(self, data: dict) -> dict:
        """Проверить вводимые данные."""
        user = self.context.get('request').user
        author = data.get('author')
        if user == author:
            raise ValidationError('Вы не можете подписаться на самого себя.')
        if Subscription.objects.filter(user=user, author=author).exists():
            raise ValidationError('Вы уже подписаны на этого автора.')
        return data

    def to_representation(self, instance: Subscription) -> dict:
        """Преобразовать данные для выдачи ответа."""
        return AuthorSerializer(instance.author, context=self.context).data


class BaseRecipeActionSerializer(ModelSerializer):
    """Базовый сериализатор для действий с рецептами."""

    duplicate_error_message = 'Рецепт уже был добавлен.'

    class Meta:
        fields = ('user', 'recipe')
        read_only_fields = ('user', 'recipe')

    def validate(self, data: dict) -> dict:
        """Проверить вводимые данные."""
        user = self.context.get('request').user
        recipe = self.context.get('recipe')
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(self.duplicate_error_message)
        return data

    def to_representation(self, instance: Model) -> dict:
        """Преобразовать данные для выдачи ответа."""
        return ShortRecipeSerializer(
            instance.recipe, context=self.context).data


class ShoppingCartSerializer(BaseRecipeActionSerializer):
    """Сериализатор списка покупок. Наследование от базового сериализатора."""

    duplicate_error_message = 'Рецепт уже добавлен в Ваш список покупок.'

    class Meta(BaseRecipeActionSerializer.Meta):
        model = ShoppingCart


class FavouriteSerializer(BaseRecipeActionSerializer):
    """Сериализатор избранного. Наследование от базового сериализатора."""

    duplicate_error_message = 'Рецепт уже добавлен в Ваше избранное.'

    class Meta(BaseRecipeActionSerializer.Meta):
        model = Favourite
