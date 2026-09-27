"""Модели приложения users."""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .constants import (MAX_EMAIL_LENGTH, MAX_FIRST_NAME_LENGTH,
                        MAX_LAST_NAME_LENGTH, MAX_USERNAME_LENGTH)
from .validators import (validate_username_characters,
                         validate_username_not_forbidden)


class CustomUserManager(BaseUserManager):
    """Кастомный менеджер для модели пользователя."""

    def create_user(
        self,
        email: str,
        username: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        **extra_fields
    ) -> AbstractUser:
        """Переопределить создание пользователя."""
        if not email:
            raise ValueError('Электронная почта обязательна')
        if not username:
            raise ValueError('Имя пользователя (никнейм) обязательно')
        if not first_name:
            raise ValueError('Имя обязательно')
        if not last_name:
            raise ValueError('Фамилия обязательна')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        username: str,
        first_name: str,
        last_name: str,
        password: str | None = None,
        **extra_fields
    ) -> AbstractUser:
        """Переопределить создание суперпользователя."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if not (
            extra_fields.get('is_staff')
            and extra_fields.get('is_superuser')
        ):
            raise ValueError(
                'Суперпользователь должен иметь права staff и superuser.')
        return self.create_user(
            email,
            username,
            first_name,
            last_name,
            password,
            **extra_fields
        )


class CustomUser(AbstractUser):
    """Кастомная модель пользователя."""

    first_name = models.CharField(
        'Имя',
        blank=False,
        max_length=MAX_FIRST_NAME_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        blank=False,
        max_length=MAX_LAST_NAME_LENGTH,
    )
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=MAX_USERNAME_LENGTH,
        unique=True,
        validators=(
            validate_username_characters,
            validate_username_not_forbidden,
        ),
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/',
        blank=True,
        null=True,
    )

    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('id',)

    def __str__(self) -> str:
        """Вернуть username пользователя."""
        return self.username


class Subscription(models.Model):
    """Модель подписки."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        CustomUser,
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
