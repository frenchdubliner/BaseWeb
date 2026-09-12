from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.captcha import verify_captcha
from apps.security.utils import get_client_ip

from .validators import validate_international_phone_number

User = get_user_model()


class CaptchaMixin(serializers.Serializer):
    captcha_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    captcha_provider = serializers.ChoiceField(
        choices=["turnstile", "recaptcha"], required=False, default="turnstile"
    )

    def _verify_captcha(self, attrs):
        request = self.context.get("request")
        remote_ip = get_client_ip(request) if request else None
        ok = verify_captcha(
            attrs.get("captcha_token"), remote_ip, attrs.get("captcha_provider", "turnstile")
        )
        if not ok:
            raise serializers.ValidationError({"captcha_token": "Captcha verification failed."})


class RegisterSerializer(CaptchaMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "phone_number",
            "dropoff_location",
            "payment_preference",
            "captcha_token",
            "captcha_provider",
        ]

    def validate_phone_number(self, value):
        return validate_international_phone_number(value)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        self._verify_captcha(attrs)

        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        transient_user = User(
            email=attrs.get("email"),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        validate_password(attrs["password"], user=transient_user)
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data.pop("captcha_token", None)
        validated_data.pop("captcha_provider", None)
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(CaptchaMixin, TokenObtainPairSerializer):
    def validate(self, attrs):
        self._verify_captcha(attrs)
        data = super().validate(attrs)
        data["user"] = UserProfileSerializer(self.user).data
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "dropoff_location",
            "payment_preference",
            "is_active",
            "mfa_enabled",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "is_active", "mfa_enabled", "date_joined"]

    def validate_phone_number(self, value):
        return validate_international_phone_number(value)


class ResendVerificationSerializer(CaptchaMixin, serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        self._verify_captcha(attrs)
        return attrs


class PasswordResetRequestSerializer(CaptchaMixin, serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        self._verify_captcha(attrs)
        return attrs


class PasswordResetConfirmSerializer(CaptchaMixin, serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        self._verify_captcha(attrs)
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        validate_password(attrs["new_password"], user=self.context["request"].user)
        return attrs
