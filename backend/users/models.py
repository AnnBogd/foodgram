"""Модели приложения users."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import MAX_FIRST_NAME_LENGTH, MAX_LAST_NAME_LENGTH


class AppUser(AbstractUser):
    """Кастомная модель пользователя."""

    first_name = models.CharField(
        'Имя',
        max_length=MAX_FIRST_NAME_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_LAST_NAME_LENGTH,
    )
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/',
        blank=True,
        null=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self) -> str:
        """Вернуть username пользователя."""
        return self.username


class Subscription(models.Model):
    """Модель подписки."""

    user = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        AppUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор рецептов',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='user_prevent_self_follow'
            )
        ]

    def __str__(self) -> str:
        """Определить строковое представление подписки."""
        return f'{self.user.username} подписан на {self.author.username}'
