from django.contrib.admin.models import LogEntry
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=LogEntry)
def log_admin_action(sender, instance, created, **kwargs):
    if not created:
        return

    from apps.audit.models import AuditLog

    AuditLog.objects.create(
        event_type=AuditLog.EventType.ADMIN_ACTION,
        actor=instance.user,
        metadata={
            "action_flag": instance.action_flag,
            "object_repr": instance.object_repr,
            "change_message": instance.get_change_message(),
            "content_type": str(instance.content_type) if instance.content_type else None,
        },
    )
