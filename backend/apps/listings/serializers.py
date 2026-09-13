from rest_framework import serializers

from .models import CONDITION_DESCRIPTIONS, GameListing


class GameListingSerializer(serializers.ModelSerializer):
    condition_description = serializers.SerializerMethodField()

    class Meta:
        model = GameListing
        fields = [
            "id",
            "game_name",
            "price",
            "condition",
            "condition_description",
            "has_missing_pieces",
            "smoking_household",
            "musty_smell",
            "pet_exposure",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_condition_description(self, obj):
        return CONDITION_DESCRIPTIONS.get(obj.condition, "")

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
