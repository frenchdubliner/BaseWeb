from rest_framework import serializers

from .models import ConventionSettings


class ConventionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConventionSettings
        fields = ["id", "name", "updated_at"]
        read_only_fields = ["id", "updated_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Convention name cannot be blank.")
        return value
