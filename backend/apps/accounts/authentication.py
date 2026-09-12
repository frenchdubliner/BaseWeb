from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings


class ActiveOrPendingJWTAuthentication(JWTAuthentication):
    """
    Identical to SimpleJWT's default JWTAuthentication, except it does not
    reject unverified (is_active=False) users when resolving the token's
    user. Unverified users must still be able to log in, log out, view
    their profile, and resend the verification email; per-endpoint
    permissions (see apps.accounts.permissions.IsVerified) enforce the
    is_active requirement everywhere else.
    """

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))

        try:
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")

        return user
