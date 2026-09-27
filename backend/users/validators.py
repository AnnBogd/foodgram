"""Валидаторы приложения users."""

from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

validate_username_characters = UnicodeUsernameValidator()


def validate_username_not_forbidden(value: str) -> None:
    """Запретить использование служебных имён пользователей."""
    if value.lower() in settings.FORBIDDEN_USERNAMES:
        raise ValidationError(
            'Использовать это имя в качестве username запрещено.'
        )
