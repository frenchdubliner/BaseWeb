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
    )


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
