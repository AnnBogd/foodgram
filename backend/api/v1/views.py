"""представления первой версии приложения api."""

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    AvatarSerializer,
    SubscriptionSerializer
)
from users.models import Subscription

current_user = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет юзера для расширения базового вьюсета djoser."""

    def destroy(self, request, *args, **kwargs):
        """Полностью удалить эндпоинт DELETE /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        """Полностью удалить эндпоинт PUT /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        """Полностью удалить эндпоинт PATCH /api/users/{id}/"""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request, *args, **kwargs):
        """Ограничить методы для эндпоинта /api/users/me/."""
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request) -> Response:
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
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request: Request, pk=None) -> Response:
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
    def avatar(self, request):
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
