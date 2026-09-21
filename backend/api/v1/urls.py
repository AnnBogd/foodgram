"""URLS первой версии приложения api."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomUserViewSet

api_v1_router = DefaultRouter()
api_v1_router.register('users', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(api_v1_router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
