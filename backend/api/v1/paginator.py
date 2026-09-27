"""Кастомные пагинаторы первой версии приложения api."""

from rest_framework.pagination import PageNumberPagination


class CustomPaginator(PageNumberPagination):
    """Кастомный класс пагинатора."""

    page_size_query_param = 'limit'
    page_size = 6
