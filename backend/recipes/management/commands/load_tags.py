import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from recipes.models import Tag


class Command(BaseCommand):
    help = 'Загрузить теги из JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default=str(Path(settings.BASE_DIR).parent / 'data' / 'tags.json'),
        )

    def handle(self, *args, **options):
        file_path = Path(options['path'])
        if not file_path.exists():
            raise CommandError(f'Файл не найден: {file_path}')

        with file_path.open(encoding='utf-8') as f:
            data = json.load(f)

        tags = [Tag(**item) for item in data]
        Tag.objects.bulk_create(tags, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f'Загружено тегов: {len(tags)}'))
