"""URLS проекта."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        's/<int:id>/',
        RedirectView.as_view(url='/recipes/%(id)s/', permanent=True)
    ),
    path('api/', include('api.v1.urls')),
]
