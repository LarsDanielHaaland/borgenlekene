"""Project URL configuration that proxies to the existing project's urls.

This module exists to allow DJANGO_SETTINGS_MODULE and ROOT_URLCONF to
reference `project.urls` while preserving the current `mymobilesite.urls`.
"""

from django.urls import include, path

urlpatterns = [
    # Delegate to the original project's URLconf
    path('', include('mymobilesite.urls')),
]
