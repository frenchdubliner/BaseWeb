from django.urls import path

from .views import ConventionSettingsView

urlpatterns = [
    path("", ConventionSettingsView.as_view(), name="convention-settings"),
]
