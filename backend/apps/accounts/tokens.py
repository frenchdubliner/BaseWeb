"""
Signed, time-limited tokens for email verification and password reset.

Uses Django's cryptographic signing (HMAC with SECRET_KEY) rather than
storing tokens in the database - the token itself carries its expiry.
"""
from django.core import signing

EMAIL_VERIFICATION_SALT = "apps.accounts.email-verification"
PASSWORD_RESET_SALT = "apps.accounts.password-reset"

EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 48  # 48 hours
PASSWORD_RESET_MAX_AGE = 60 * 60 * 2  # 2 hours


def make_email_verification_token(user) -> str:
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=EMAIL_VERIFICATION_SALT)


def read_email_verification_token(token: str):
    try:
        return signing.loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=EMAIL_VERIFICATION_MAX_AGE)
    except signing.BadSignature:
        return None


def make_password_reset_token(user) -> str:
    # Include the password hash so the token is invalidated once used.
    return signing.dumps(
        {"uid": user.pk, "pw": user.password[-16:]}, salt=PASSWORD_RESET_SALT
    )


def read_password_reset_token(token: str):
    try:
        return signing.loads(token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE)
    except signing.BadSignature:
        return None
