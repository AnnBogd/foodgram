"""Кастомные пермишены первой версии приложения api."""

from django.db.models import Model
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticatedOrReadOnly, SAFE_METHODS
from rest_framework.viewsets import ModelViewSet


class IsAuthorOrReadOnly(IsAuthenticatedOrReadOnly):
    """Определить авторство рецепта."""

    def has_object_permission(
            self,
            request: Request,
            view: ModelViewSet,
            obj: Model
    ) -> bool:
        """Определить авторство рецепта."""
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user
