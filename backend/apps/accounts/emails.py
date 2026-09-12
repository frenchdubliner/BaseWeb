from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.tokens import make_email_verification_token, make_password_reset_token


def send_verification_email(user):
    token = make_email_verification_token(user)
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    send_mail(
        subject="Verify your email address",
        message=(
            f"Hi {user.first_name},\n\n"
            f"Please verify your email address by visiting the link below. "
            f"This link expires in 48 hours.\n\n{verify_url}\n\n"
            "If you did not create this account, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    token = make_password_reset_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    send_mail(
        subject="Reset your password",
        message=(
            f"Hi {user.first_name},\n\n"
            f"A password reset was requested for your account. This link expires "
            f"in 2 hours.\n\n{reset_url}\n\n"
            "If you did not request this, you can safely ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
