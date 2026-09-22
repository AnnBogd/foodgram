"""URLS первой версии приложения api."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomUserViewSet,
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet
)

api_v1_router = DefaultRouter()
api_v1_router.register('users', CustomUserViewSet, basename='users')
api_v1_router.register(
    'ingredients', IngredientViewSet, basename='ingredients')
api_v1_router.register('tags', TagViewSet, basename='tags')
api_v1_router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(api_v1_router.urls)),
]
