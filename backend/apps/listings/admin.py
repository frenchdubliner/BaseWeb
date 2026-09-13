from django.contrib import admin

from .models import GameListing


@admin.register(GameListing)
class GameListingAdmin(admin.ModelAdmin):
    list_display = (
        "game_name",
        "owner",
        "price",
        "condition",
        "has_missing_pieces",
        "smoking_household",
        "musty_smell",
        "pet_exposure",
        "created_at",
    )
    list_filter = ("condition", "has_missing_pieces", "smoking_household", "musty_smell", "pet_exposure")
    search_fields = ("game_name", "owner__email")
