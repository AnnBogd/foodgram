"""URLS проекта."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        's/<int:pk>/',
        RedirectView.as_view(pattern_name='recipes-detail', permanent=True)
    ),
    path('api/', include('api.v1.urls')),
]
