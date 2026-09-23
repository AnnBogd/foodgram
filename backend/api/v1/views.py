"""представления первой версии приложения api."""

from django.contrib.auth import get_user_model
from django.db.models import (
    Case,
    Model,
    QuerySet,
    Sum,
    When,
    Value,
    IntegerField
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import (
    Favourite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag
)
from users.models import Subscription
from .filters import RecipeFilter
from .serializers import (
    AvatarSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortRecipeSerializer,
    SubscriptionSerializer,
    IngredientSerializer,
    TagSerializer
)

current_user = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет юзера для расширения базового вьюсета djoser."""

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Полностью удалить эндпоинт DELETE /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Полностью удалить эндпоинт PUT /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """Полностью удалить эндпоинт PATCH /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request: Request, *args, **kwargs) -> Model:
        """Ограничить методы для эндпоинта /api/users/me/."""
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request: Request) -> Response:
        """Вернуть список подписок текущего пользователя."""
        user = request.user
        authors = current_user.objects.filter(following__user=user)
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request: Request, pk: int = None) -> Response:
        """Создать или удалить подписку."""
        user = request.user
        author = get_object_or_404(current_user, pk=pk)
        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Вы не можете подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(user=user, author=author).exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            subscription = Subscription.objects.filter(
                user=user, author=author)
            if subscription.exists():
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'errors': 'Вы не были подписаны на этого автора.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request: Request) -> Response:
        """Добавить или удалить аватар."""
        user = request.user
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                user, data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet:
        """Получить выборку ингредиентов в зависимости от поиска."""
        queryset = super().get_queryset()
        name_query = self.request.query_params.get('name')
        if name_query:
            name_query = name_query.lower()
            queryset = (
                queryset.filter(name__istartswith=name_query)
                | queryset.filter(name__icontains=name_query)
            )
            queryset = queryset.annotate(
                search_order=Case(
                    When(name__istartswith=name_query, then=Value(1)),
                    When(name__icontains=name_query, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            ).order_by('search_order', 'name')
        return queryset


class RecipeViewSet(ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete')
    filterset_class = RecipeFilter

    def get_serializer_class(self) -> Serializer:
        """Выбрать сериализатор в зависимости от действия."""
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[AllowAny]
    )
    def get_link(self, request: Request, pk=None) -> Response:
        """Получить короткую ссылку на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(f'/s/{recipe.id}/')
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request: Request) -> Response:
        """Скачать текстовый файл со списком покупок."""
        user = request.user
        if not ShoppingCart.objects.filter(user=user).exists():
            return Response(
                {'errors': 'Ваш список покупок пуст.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ingredients = (
            IngredientRecipe.objects
            .filter(recipe__shopping_cart__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        shopping_list = [
            f'Список покупок для пользователя {user.get_full_name()}.\n'
        ]
        for item in ingredients:
            shopping_list.append(
                f'* {item["ingredient__name"]} - '
                f'{item["total_amount"]} '
                f'{item["ingredient__measurement_unit"]}\n'
            )
        file_content = ''.join(shopping_list)
        response = HttpResponse(
            file_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"')
        return response

    def _manage_recipe_relation(
            self,
            request: Request,
            pk: int,
            model: Model,
            error_add: str,
            error_del: str
    ) -> Response:
        """Определить логику добавления/удаления рецепта."""
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if model.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'errors': error_add},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = ShortRecipeSerializer(
                recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            model_object = model.objects.filter(
                user=user, recipe=recipe)
            if model_object.exists():
                model_object.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'errors': error_del},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    def manage_shopping_cart(
            self, request: Request, pk: int = None) -> Response:
        """Добавить или удалить рецепт в список покупок."""
        return self._manage_recipe_relation(
            request=request,
            pk=pk,
            model=ShoppingCart,
            error_add='Рецепт уже добавлен в Ваш список покупок.',
            error_del='Этого рецепта не было в Вашем списке покупок.'
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def manage_favorite(
            self, request: Request, pk: int = None) -> Response:
        """Добавить или удалить рецепт в избранное."""
        return self._manage_recipe_relation(
            request=request,
            pk=pk,
            model=Favourite,
            error_add='Рецепт уже добавлен в Ваше избранное.',
            error_del='Этого рецепта не было в Вашем избранном.'
        )
