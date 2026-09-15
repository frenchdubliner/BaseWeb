from rest_framework import serializers

from .models import CONDITION_DESCRIPTIONS, GameListing


class GameListingSerializer(serializers.ModelSerializer):
    condition_description = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = GameListing
        fields = [
            "id",
            "game_name",
            "price",
            "condition",
            "condition_description",
            "has_missing_pieces",
            "missing_pieces_description",
            "smoking_household",
            "musty_smell",
            "pet_exposure",
            "comments",
            "can_edit",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_condition_description(self, obj):
        return CONDITION_DESCRIPTIONS.get(obj.condition, "")

    def get_can_edit(self, obj):
        # A capability flag, not the underlying reason - the `printed`
        # attribute itself stays admin-only and is never exposed here.
        return not obj.printed

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate(self, attrs):
        # Don't let a stale description linger once "has missing pieces" is
        # explicitly unchecked in the same request.
        if attrs.get("has_missing_pieces") is False:
            attrs["missing_pieces_description"] = ""
        return attrs


class AdminGameListingSerializer(GameListingSerializer):
    """Used by the admin-only listings endpoint - adds owner details for
    display/filtering and keeps owner itself read-only (reassigning a
    listing to a different user is out of scope)."""

    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    owner_first_name = serializers.CharField(source="owner.first_name", read_only=True)
    owner_last_name = serializers.CharField(source="owner.last_name", read_only=True)
    owner_dropoff_location = serializers.CharField(source="owner.dropoff_location", read_only=True)

    class Meta(GameListingSerializer.Meta):
        fields = GameListingSerializer.Meta.fields + [
            "owner",
            "owner_email",
            "owner_first_name",
            "owner_last_name",
            "owner_dropoff_location",
            "printed",
            "received",
        ]
        # printed is admin-visible but not admin-editable here - it's only
        # ever set by the print/print-all actions, never by a direct edit.
        # received IS admin-editable (that's the whole point of the toggle
        # button), it's just excluded from GameListingSerializer entirely,
        # same as printed, so the owner never sees or sets either one.
        read_only_fields = GameListingSerializer.Meta.read_only_fields + ["owner", "printed"]
