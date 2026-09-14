from rest_framework.routers import DefaultRouter, SimpleRouter

from django.urls import path

from .views import (
    AdminGameListingViewSet,
    GameListingBulkUploadView,
    GameListingCSVTemplateView,
    GameListingViewSet,
)

# SimpleRouter (not DefaultRouter) for the admin sub-routes: DefaultRouter
# auto-generates an "API root" view bound to the empty path, and two of
# those in the same urls.py collide (whichever is listed first shadows the
# other's list/create route entirely, since both claim the same URL).
admin_router = SimpleRouter()
admin_router.register("admin", AdminGameListingViewSet, basename="admin-game-listing")

router = DefaultRouter()
router.register("", GameListingViewSet, basename="game-listing")

urlpatterns = (
    [
        # Must come before router.urls: the plain router's detail route
        # (`<pk>/`) would otherwise greedily match these as if they were a
        # listing ID.
        path("bulk-upload/", GameListingBulkUploadView.as_view(), name="game-listing-bulk-upload"),
        path("csv-template/", GameListingCSVTemplateView.as_view(), name="game-listing-csv-template"),
    ]
    + admin_router.urls
    + router.urls
)
