from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import LoginAudit

from .helpers import make_user


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")

    def test_active_user_can_login_and_audit_is_logged(self):
        make_user(email="active@example.com", is_active=True)
        response = self.client.post(
            self.login_url, {"email": "active@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(
            LoginAudit.objects.filter(
                email_attempted="active@example.com", action=LoginAudit.Action.LOGIN_SUCCESS
            ).exists()
        )

    def test_inactive_user_can_still_login(self):
        make_user(email="inactive@example.com", is_active=False)
        response = self.client.post(
            self.login_url,
            {"email": "inactive@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["user"]["is_active"])

    def test_wrong_password_rejected_and_audited(self):
        make_user(email="active2@example.com", is_active=True)
        response = self.client.post(
            self.login_url, {"email": "active2@example.com", "password": "WrongPass!1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(
            LoginAudit.objects.filter(
                email_attempted="active2@example.com", action=LoginAudit.Action.LOGIN_FAILURE
            ).exists()
        )

    def test_logout_blacklists_refresh_and_logs_audit(self):
        make_user(email="active3@example.com", is_active=True)
        login_response = self.client.post(
            self.login_url,
            {"email": "active3@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        access = login_response.data["access"]
        refresh = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.post(self.logout_url, {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertTrue(
            LoginAudit.objects.filter(
                email_attempted="active3@example.com", action=LoginAudit.Action.LOGOUT
            ).exists()
        )

        # The blacklisted refresh token can no longer mint new access tokens.
        refresh_response = self.client.post(reverse("login-refresh"), {"refresh": refresh}, format="json")
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
