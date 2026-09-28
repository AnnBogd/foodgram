"""URLS проекта."""

from api.v1.views import recipe_short_link
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('s/<str:code>', recipe_short_link, name='short-link'),
    path('api/', include('api.v1.urls')),
]
