from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.accounts.models import User


@receiver(user_login_failed)
def handle_login_failed(sender, credentials, request=None, **kwargs):
    from apps.audit.models import LoginAudit
    from apps.security.utils import get_client_ip

    if request is None:
        return
    # Credentials are keyed by USERNAME_FIELD ("email" here), not "username".
    email_attempted = credentials.get(User.USERNAME_FIELD) or credentials.get("username", "")
    LoginAudit.objects.create(
        user=None,
        email_attempted=email_attempted,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        action=LoginAudit.Action.LOGIN_FAILURE,
        reason=_login_failure_reason(request),
    )


def _login_failure_reason(request):
    """
    Best-effort reason for a login failure, for admin diagnostics only -
    never exposed to the client (SimpleJWT returns one generic message
    either way, to avoid leaking which emails are registered).

    Unverified (is_active=False) accounts are NOT a failure reason here -
    apps.accounts.backends.EmailBackend deliberately lets them authenticate
    successfully; they're restricted per-endpoint afterward (IsVerified),
    not at login. So the only two ways authenticate() actually fails are
    a locked-out ip+email pair, or genuinely wrong credentials.

    `axes` is listed before `apps.accounts` in INSTALLED_APPS, so its own
    `user_login_failed` receiver - which sets `request.axes_locked_out` when
    this attempt is rejected due to lockout - runs and updates `request`
    before this receiver does.
    """
    from apps.audit.models import LoginAudit

    if getattr(request, "axes_locked_out", False):
        return LoginAudit.Reason.LOCKED_OUT
    return LoginAudit.Reason.INVALID_CREDENTIALS


@receiver(pre_save, sender=User)
def track_role_and_email_changes(sender, instance: User, **kwargs):
    if not instance.pk:
        return
    try:
        previous = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    from apps.audit.models import AuditLog

    if previous.is_staff != instance.is_staff or previous.is_superuser != instance.is_superuser:
        AuditLog.objects.create(
            event_type=AuditLog.EventType.ROLE_CHANGE,
            actor=instance,
            target_user=instance,
            metadata={
                "was_staff": previous.is_staff,
                "is_staff": instance.is_staff,
                "was_superuser": previous.is_superuser,
                "is_superuser": instance.is_superuser,
            },
        )

    if previous.email != instance.email:
        AuditLog.objects.create(
            event_type=AuditLog.EventType.EMAIL_CHANGE,
            actor=instance,
            target_user=instance,
            metadata={"old_email": previous.email, "new_email": instance.email},
        )
