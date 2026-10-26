from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.audit.models import LoginAudit

from .helpers import make_user


class LoginFailureReasonTests(APITestCase):
    """
    The admin-facing LoginAudit log records *why* a login failed, not just
    that it failed - this covers each of the three reasons the login view
    can produce, via the real endpoint end-to-end (not just unit-testing
    the reason-lookup helper), since the interesting part is whether the
    signal ordering with axes actually behaves as expected in practice.
    """

    def setUp(self):
        cache.clear()
        self.login_url = reverse("login")

    def test_wrong_password_is_invalid_credentials(self):
        make_user(email="active@example.com", is_active=True)
        self.client.post(
            self.login_url, {"email": "active@example.com", "password": "WrongPass!1"}, format="json"
        )
        entry = LoginAudit.objects.filter(email_attempted="active@example.com").latest("timestamp")
        self.assertEqual(entry.reason, LoginAudit.Reason.INVALID_CREDENTIALS)

    def test_unknown_email_is_invalid_credentials(self):
        self.client.post(
            self.login_url, {"email": "nobody@example.com", "password": "WrongPass!1"}, format="json"
        )
        entry = LoginAudit.objects.filter(email_attempted="nobody@example.com").latest("timestamp")
        self.assertEqual(entry.reason, LoginAudit.Reason.INVALID_CREDENTIALS)

    def test_unverified_account_with_correct_password_logs_in_successfully(self):
        # apps.accounts.backends.EmailBackend deliberately lets unverified
        # (is_active=False) accounts authenticate - they're restricted
        # per-endpoint afterward, not at login - so this is a SUCCESS row,
        # not a failure with some "inactive" reason.
        make_user(email="pending@example.com", is_active=False)
        response = self.client.post(
            self.login_url, {"email": "pending@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        entry = LoginAudit.objects.filter(email_attempted="pending@example.com").latest("timestamp")
        self.assertEqual(entry.action, LoginAudit.Action.LOGIN_SUCCESS)
        self.assertEqual(entry.reason, "")

    def test_lockout_after_failure_limit_is_locked_out_reason(self):
        make_user(email="locktarget@example.com", is_active=True)
        for _ in range(5):
            self.client.post(
                self.login_url,
                {"email": "locktarget@example.com", "password": "WrongPass!1"},
                format="json",
            )
        # One more attempt, this time with the CORRECT password - still
        # rejected, but now for a different reason (locked out, not a
        # credentials problem) - the whole point of a "reason" field.
        self.client.post(
            self.login_url,
            {"email": "locktarget@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        entry = LoginAudit.objects.filter(email_attempted="locktarget@example.com").latest("timestamp")
        self.assertEqual(entry.reason, LoginAudit.Reason.LOCKED_OUT)

    def test_successful_login_has_no_reason(self):
        make_user(email="active@example.com", is_active=True)
        self.client.post(
            self.login_url, {"email": "active@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        entry = LoginAudit.objects.filter(email_attempted="active@example.com").latest("timestamp")
        self.assertEqual(entry.action, LoginAudit.Action.LOGIN_SUCCESS)
        self.assertEqual(entry.reason, "")
