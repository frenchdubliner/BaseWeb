from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GameListingBulkUploadView, GameListingCSVTemplateView, GameListingViewSet

router = DefaultRouter()
router.register("", GameListingViewSet, basename="game-listing")

urlpatterns = [
    # Must come before router.urls: the router's detail route (`<pk>/`)
    # would otherwise greedily match these as if they were a listing ID.
    path("bulk-upload/", GameListingBulkUploadView.as_view(), name="game-listing-bulk-upload"),
    path("csv-template/", GameListingCSVTemplateView.as_view(), name="game-listing-csv-template"),
] + router.urls
