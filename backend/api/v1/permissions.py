"""Кастомные пермишены первой версии приложения api."""

from django.db.models import Model
from rest_framework.permissions import (SAFE_METHODS, BasePermission,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet


class IsAdminOrReadOnly(BasePermission):
    """Определить права в эндпоинтах users."""

    def has_permission(self, request: Request, view: ModelViewSet) -> bool:
        """Определить права на уровне запроса."""
        return (request.method in SAFE_METHODS
                or (request.user and request.user.is_staff))


class IsAuthorOrReadOnly(IsAuthenticatedOrReadOnly):
    """Определить авторство рецепта."""

    def has_object_permission(
            self,
            request: Request,
            view: ModelViewSet,
            obj: Model
    ) -> bool:
        """Определить авторство рецепта."""
        return request.method in SAFE_METHODS or obj.author == request.user
