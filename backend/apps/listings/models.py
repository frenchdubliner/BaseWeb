from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class GameCondition(models.TextChoices):
    NEW_IN_SHRINK = "new_in_shrink", _("New in Shrink")
    LIKE_NEW = "like_new", _("Like New")
    VERY_GOOD = "very_good", _("Very Good")
    GOOD = "good", _("Good")
    FAIR = "fair", _("Fair")
    POOR = "poor", _("Poor")


CONDITION_DESCRIPTIONS = {
    GameCondition.NEW_IN_SHRINK: _("Original shrink wrap. Never opened."),
    GameCondition.LIKE_NEW: _("Pieces unpunched, cards wrapped, never played."),
    GameCondition.VERY_GOOD: _(
        "Pieces punched, sorted, rarely or never played. No discernible wear."
    ),
    GameCondition.GOOD: _("Played but well maintained, pieces unsorted, box shows signs of use."),
    GameCondition.FAIR: _(
        "Discernible wear. Box/book show minor damage and have been slightly marked."
    ),
    GameCondition.POOR: _(
        "Worn but playable. Box/book show damage and/or have been significantly marked."
    ),
}


class PetExposure(models.TextChoices):
    CAT = "cat", _("Cat")
    DOG = "dog", _("Dog")
    MULTIPLE = "multiple", _("Multiple pets")


class GameListing(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    game_name = models.CharField(_("game name"), max_length=200)
    price = models.DecimalField(
        _("price"), max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    condition = models.CharField(_("condition"), max_length=20, choices=GameCondition.choices)
    has_missing_pieces = models.BooleanField(_("has missing pieces"), default=False)
    missing_pieces_description = models.CharField(
        _("missing pieces description"),
        max_length=64,
        blank=True,
        help_text=_("Which piece(s) are missing, e.g. \"2 red meeples, 1 die\"."),
    )
    smoking_household = models.BooleanField(_("exposed to smoking household"), default=False)
    musty_smell = models.BooleanField(_("has musty smell"), default=False)
    pet_exposure = models.CharField(
        _("pet exposure"),
        max_length=20,
        choices=PetExposure.choices,
        blank=True,
        help_text=_("Leave blank if the game was not exposed to any pets."),
    )
    comments = models.CharField(_("comments"), max_length=64, blank=True)
    printed = models.BooleanField(
        _("printed"),
        default=False,
        help_text=_(
            "Set automatically when an admin prints this listing's price tag. "
            "Admin-only - never exposed to or editable by the listing's owner, "
            "including via CSV import. Once True, only an admin can edit or "
            "delete the listing."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "created_at"])]

    def __str__(self):
        return f"{self.game_name} ({self.owner.email})"
