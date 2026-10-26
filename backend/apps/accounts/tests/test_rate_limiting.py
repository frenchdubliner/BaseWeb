from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from apps.audit.models import AuditLog

from .helpers import make_user, registration_payload


class AxesLockoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("login")
        make_user(email="locktarget@example.com", is_active=True)

    def test_account_locks_out_after_repeated_failures(self):
        for _ in range(5):
            response = self.client.post(
                self.login_url,
                {"email": "locktarget@example.com", "password": "WrongPass!1"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Even the correct password should now be rejected while locked out.
        response = self.client.post(
            self.login_url,
            {"email": "locktarget@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_other_user_on_same_ip_not_locked_out_by_unrelated_failures(self):
        # Regression guard: AXES_LOCKOUT_PARAMETERS must combine ip+username
        # into one key, not treat them as independent lockout buckets - a
        # flat ["ip_address", "username"] would lock out every account on a
        # shared IP (e.g. shop/convention WiFi) once *any* account on that
        # IP racks up failures, which is exactly the bug this guards against.
        make_user(email="innocent@example.com", is_active=True)
        for _ in range(5):
            self.client.post(
                self.login_url,
                {"email": "locktarget@example.com", "password": "WrongPass!1"},
                format="json",
            )

        # Same test-client IP, different account, correct password - must
        # succeed despite locktarget's IP-visible failures above.
        response = self.client.post(
            self.login_url,
            {"email": "innocent@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)


class RegistrationThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("register")

    def test_registration_is_rate_limited(self):
        # ScopedRateThrottle reads its rates from a class attribute snapshotted
        # at import time, so override it directly rather than via
        # override_settings (which would not be picked up by the class).
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "2/min"}):
            statuses = []
            for i in range(3):
                response = self.client.post(
                    self.url, registration_payload(email=f"throttle{i}@example.com"), format="json"
                )
                statuses.append(response.status_code)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)

    def test_rate_limit_exceeded_is_logged_to_audit_log(self):
        # A 429 is rejected in APIView.initial(), before the view method
        # runs, so this can only be caught at the exception-handler layer
        # (apps.security.exceptions.audit_logging_exception_handler) - not
        # by any view-level logging code, which never executes for these.
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "2/min"}):
            for i in range(3):
                self.client.post(
                    self.url, registration_payload(email=f"auditthrottle{i}@example.com"), format="json"
                )

        entry = AuditLog.objects.filter(event_type=AuditLog.EventType.RATE_LIMIT_EXCEEDED).latest("timestamp")
        self.assertEqual(entry.metadata["throttle_scope"], "register")
        self.assertEqual(entry.metadata["path"], self.url)
        self.assertIn("wait_seconds", entry.metadata)

    def test_requests_within_the_limit_are_not_logged(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "5/min"}):
            self.client.post(self.url, registration_payload(email="withinlimit@example.com"), format="json")
        self.assertFalse(
            AuditLog.objects.filter(event_type=AuditLog.EventType.RATE_LIMIT_EXCEEDED).exists()
        )
