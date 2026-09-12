from django.test import TestCase

from apps.audit.models import AuditLog, LoginAudit


class LoginAuditModelTests(TestCase):
    def test_success_flag_derived_from_action(self):
        success = LoginAudit.objects.create(
            action=LoginAudit.Action.LOGIN_SUCCESS, email_attempted="a@example.com"
        )
        failure = LoginAudit.objects.create(
            action=LoginAudit.Action.LOGIN_FAILURE, email_attempted="a@example.com"
        )
        self.assertTrue(success.success)
        self.assertFalse(failure.success)

    def test_logout_is_recorded_as_success(self):
        entry = LoginAudit.objects.create(action=LoginAudit.Action.LOGOUT, email_attempted="a@example.com")
        self.assertTrue(entry.success)


class AuditLogModelTests(TestCase):
    def test_metadata_defaults_to_empty_dict(self):
        entry = AuditLog.objects.create(event_type=AuditLog.EventType.ADMIN_ACTION)
        self.assertEqual(entry.metadata, {})

    def test_ordering_is_most_recent_first(self):
        first = AuditLog.objects.create(event_type=AuditLog.EventType.ADMIN_ACTION)
        second = AuditLog.objects.create(event_type=AuditLog.EventType.ADMIN_ACTION)
        self.assertEqual(list(AuditLog.objects.all()), [second, first])
