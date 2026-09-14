from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Battleground Used Games Administration"
admin.site.site_title = "Battleground Used Games Admin"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/listings/", include("apps.listings.urls")),
    path("api/convention/", include("apps.convention.urls")),
]
