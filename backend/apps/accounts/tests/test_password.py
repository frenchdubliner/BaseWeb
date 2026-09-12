from django.core import mail
from django.core.cache import cache
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
