"""Кастомные пагинаторы первой версии приложения api."""

from rest_framework.pagination import PageNumberPagination

PAGE_SIZE = 6


class RecipePaginator(PageNumberPagination):
    """Кастомный класс пагинатора."""

    page_size_query_param = 'limit'
    page_size = PAGE_SIZE
