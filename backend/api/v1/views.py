"""представления первой версии приложения api."""

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favourite, Ingredient, IngredientRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from users.models import Subscription

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, AuthorSerializer,
                          FavouriteSerializer, IngredientReadSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          ShoppingCartSerializer, SubscriptionSerializer,
                          TagSerializer)

current_user = get_user_model()


def recipe_short_link(request: Request, code: str) -> HttpResponseRedirect:
    """Сделать редирект с короткой ссылки на эндпоинт рецепта."""
    recipe = get_object_or_404(Recipe, short_code=code)
    return redirect(f'/recipes/{recipe.pk}/')


class ExtendedUserViewSet(UserViewSet):
    """Вьюсет для обработки эндпоинтов users."""

    def get_permissions(self) -> tuple:
        """Определить права доступа к методу."""
        if self.action in ('list', 'retrieve', 'create'):
            return (AllowAny(), )
        if self.action in ('update', 'partial_update', 'destroy'):
            return (IsAdminUser(), )
        return super().get_permissions()

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request: Request, *args, **kwargs) -> Response:
        """Посмотреть информацию о своем пользователе."""
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
        serializer = AuthorSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request: Request, id: int = None) -> Response:
        """Создать подписку на пользователя."""
        author = get_object_or_404(current_user, pk=id)
        serializer = SubscriptionSerializer(
            data={'author': author.id},
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request: Request, id: int = None) -> Response:
        """Удалить подписку на пользователя."""
        author = get_object_or_404(current_user, pk=id)
        deleted, _ = Subscription.objects.filter(
            user=request.user,
            author=author
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Вы не были подписаны на этого автора.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request: Request) -> Response:
        """Добавить аватар."""
        user = request.user
        serializer = AvatarSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @avatar.mapping.delete
    def delete_avatar(self, request: Request) -> Response:
        """Удалить аватар."""
        user = request.user
        if user.avatar:
            user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ReadOnlyModelViewSet):
    """Вьюсет для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    """Вьюсет для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientReadSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(ModelViewSet):
    """Вьюсет для рецептов."""

    queryset = Recipe.objects.all()
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = (IsAuthorOrReadOnly,)

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
        short_link = request.build_absolute_uri(f'/s/{recipe.short_code}')
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

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    def add_to_shopping_cart(
            self, request: Request, pk: int = None) -> Response:
        """Добавить рецепт в список покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShoppingCartSerializer(
            data={},
            context={'request': request, 'recipe': recipe},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_to_shopping_cart.mapping.delete
    def delete_from_shopping_cart(
            self, request: Request, pk: int = None) -> Response:
        """Удалить рецепт из списка покупок."""
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Этого рецепта не было в Вашем списке покупок.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def add_to_favorite(
            self, request: Request, pk: int = None) -> Response:
        """Добавить рецепт в избранное."""
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = FavouriteSerializer(
            data={},
            context={'request': request, 'recipe': recipe},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_to_favorite.mapping.delete
    def delete_from_favorite(
            self, request: Request, pk: int = None) -> Response:
        """Удалить рецепт из избранного."""
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = Favourite.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Этого рецепта не было в Вашем избранном.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
