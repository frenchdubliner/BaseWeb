from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LoginAudit(models.Model):
    """Dedicated audit trail for login/logout events, as required."""

    class Action(models.TextChoices):
        LOGIN_SUCCESS = "login_success", _("Login success")
        LOGIN_FAILURE = "login_failure", _("Login failure")
        LOGOUT = "logout", _("Logout")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_audits",
    )
    email_attempted = models.EmailField(blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    success = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    country = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["email_attempted", "timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def save(self, *args, **kwargs):
        self.success = self.action != self.Action.LOGIN_FAILURE
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action} - {self.email_attempted or (self.user and self.user.email)} @ {self.timestamp}"


class AuditLog(models.Model):
    """General-purpose security/audit event log covering every other
    category required: registration attempts, password changes, email
    changes, role changes, account activations, geo blocks, IP blocks and
    admin actions."""

    class EventType(models.TextChoices):
        REGISTRATION_ATTEMPT = "registration_attempt", _("Registration attempt")
        PASSWORD_CHANGE = "password_change", _("Password change")
        EMAIL_CHANGE = "email_change", _("Email change")
        ROLE_CHANGE = "role_change", _("Role change")
        ACCOUNT_ACTIVATION = "account_activation", _("Account activation")
        GEO_BLOCK = "geo_block", _("Geo block")
        IP_BLOCK = "ip_block", _("IP block")
        ADMIN_ACTION = "admin_action", _("Admin action")

    event_type = models.CharField(max_length=32, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
        help_text="The user who performed or triggered this event, if known.",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_targets",
        help_text="The user affected by this event, if any.",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp}"
