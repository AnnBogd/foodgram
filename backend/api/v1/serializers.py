"""Сериализаторы первой версии приложения api."""

from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from users.models import Subscription

current_user = get_user_model()


class CustomUserSerializer(ModelSerializer):
    """Сериализатор для отображения профиля пользователя."""

    is_subscribed = SerializerMethodField()

    class Meta:
        model = current_user
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        """Определить кастомное поле is_subscribed."""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return (
            Subscription.objects
            .filter(user=request.user, author=obj)
            .exists()
        )


class CustomUserCreateSerializer(ModelSerializer):
    """Сериализатор для создания нового пользователя."""

    class Meta:
        model = current_user
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Создать пользователя."""
        user = current_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
