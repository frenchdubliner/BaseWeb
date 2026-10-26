from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tokens import make_password_reset_token
from apps.audit.models import AuditLog

from .helpers import make_user


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.request_url = reverse("password-reset")
        self.confirm_url = reverse("password-reset-confirm")

    def test_reset_request_sends_email_for_existing_user(self):
        make_user(email="reset@example.com")
        response = self.client.post(self.request_url, {"email": "reset@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_request_silent_for_unknown_email(self):
        response = self.client.post(
            self.request_url, {"email": "unknown@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_confirm_changes_password(self):
        user = make_user(email="reset2@example.com")
        token = make_password_reset_token(user)
        response = self.client.post(
            self.confirm_url,
            {"token": token, "new_password": "BrandNew!42", "confirm_password": "BrandNew!42"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        user.refresh_from_db()
        self.assertTrue(user.check_password("BrandNew!42"))
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.PASSWORD_CHANGE, target_user=user
            ).exists()
        )

    @override_settings(CAPTCHA_ENFORCED=True)
    def test_reset_confirm_does_not_require_captcha_even_when_enforced(self):
        # Regression guard: the frontend's reset-password-confirm page never
        # rendered a CaptchaWidget (unlike every other captcha-protected
        # page), so this step was unconditionally rejected with "Captcha
        # verification failed" whenever CAPTCHA_ENFORCED was on in
        # production - never caught by the tests above because the test
        # settings leave CAPTCHA_ENFORCED off by default. This step is
        # already gated by possession of the signed, single-use,
        # short-lived emailed token, so it doesn't need a captcha too.
        user = make_user(email="reset4@example.com")
        token = make_password_reset_token(user)
        response = self.client.post(
            self.confirm_url,
            {"token": token, "new_password": "BrandNew!42", "confirm_password": "BrandNew!42"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    @override_settings(CAPTCHA_ENFORCED=True)
    def test_reset_request_still_requires_captcha_when_enforced(self):
        # The request step genuinely needs captcha protection (it's the
        # anonymous, triggerable-by-anyone form) - confirm the fix above
        # didn't accidentally weaken this one too.
        make_user(email="reset5@example.com")
        response = self.client.post(self.request_url, {"email": "reset5@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_token_cannot_be_reused(self):
        user = make_user(email="reset3@example.com")
        token = make_password_reset_token(user)
        self.client.post(
            self.confirm_url,
            {"token": token, "new_password": "BrandNew!42", "confirm_password": "BrandNew!42"},
            format="json",
        )
        second_attempt = self.client.post(
            self.confirm_url,
            {"token": token, "new_password": "SomethingElse!1", "confirm_password": "SomethingElse!1"},
            format="json",
        )
        self.assertEqual(second_attempt.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordChangeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user(email="changer@example.com")
        login = self.client.post(
            reverse("login"), {"email": "changer@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_change_password_requires_correct_current_password(self):
        response = self.client.post(
            reverse("password-change"),
            {
                "current_password": "WrongOne!1",
                "new_password": "BrandNew!42",
                "confirm_password": "BrandNew!42",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_success_is_audited(self):
        response = self.client.post(
            reverse("password-change"),
            {
                "current_password": "Sup3rSecret!42",
                "new_password": "BrandNew!42",
                "confirm_password": "BrandNew!42",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.PASSWORD_CHANGE, target_user=self.user
            ).exists()
        )
