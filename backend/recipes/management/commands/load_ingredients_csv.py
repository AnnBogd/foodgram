"""Команда для загрузки ингредиентов в базу данных из формата csv."""

import csv
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    """Класс команды заргузки."""

    help = 'Загрузка ингредиентов из CSV файла без заголовков'

    def handle(self, *args, **options):
        file_path = Path(settings.BASE_DIR).parent / 'data' / 'ingredients.csv'

        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f'Файл не найден по пути: {file_path}'))
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            ingredients_to_create = []
            for row in reader:
                ingredients_to_create.append(
                    Ingredient(
                        name=row[0],
                        measurement_unit=row[1]
                    )
                )
            Ingredient.objects.bulk_create(
                ingredients_to_create, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            'Ингредиенты из CSV успешно загружены!'))
