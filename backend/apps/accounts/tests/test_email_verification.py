from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.accounts.tokens import make_email_verification_token
from apps.audit.models import AuditLog

from .helpers import make_user


class EmailVerificationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.verify_url = reverse("verify-email")
        self.resend_url = reverse("resend-verification")

    def test_valid_token_activates_account(self):
        user = make_user(email="pending@example.com", is_active=False)
        token = make_email_verification_token(user)

        response = self.client.post(self.verify_url, {"token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ACCOUNT_ACTIVATION, target_user=user
            ).exists()
        )

    def test_invalid_token_rejected(self):
        response = self.client.post(self.verify_url, {"token": "garbage"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_verification_sends_email_for_inactive_user(self):
        make_user(email="pending2@example.com", is_active=False)
        response = self.client.post(self.resend_url, {"email": "pending2@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_verification_does_not_leak_account_existence(self):
        response = self.client.post(
            self.resend_url, {"email": "doesnotexist@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_unverified_user_can_view_profile_but_not_password_change(self):
        user = make_user(email="pending3@example.com", is_active=False)
        login = self.client.post(
            reverse("login"), {"email": "pending3@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        access = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        profile_response = self.client.get(reverse("profile"))
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)

        change_response = self.client.post(
            reverse("password-change"),
            {
                "current_password": "Sup3rSecret!42",
                "new_password": "AnotherOne!42",
                "confirm_password": "AnotherOne!42",
            },
            format="json",
        )
        self.assertEqual(change_response.status_code, status.HTTP_403_FORBIDDEN)
