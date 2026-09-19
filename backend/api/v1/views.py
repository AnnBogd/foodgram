"""Views первой версии приложения api."""

from django.contrib.auth import get_user_model
from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Кастомный вьюсет для расширения базового вьюсета djoser."""

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self) -> Response:
        """Вернуть список подписок текущего пользователя."""
        return Response(
            status=status.HTTP_200_OK
        )
