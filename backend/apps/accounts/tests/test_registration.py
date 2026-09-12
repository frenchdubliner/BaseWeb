from django.core import mail
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog

from .helpers import registration_payload


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("register")

    def test_successful_registration_creates_inactive_user_and_sends_email(self):
        response = self.client.post(self.url, registration_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(email="newuser@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("verify", mail.outbox[0].subject.lower())
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.REGISTRATION_ATTEMPT, target_user=user
            ).exists()
        )

    def test_phone_number_is_encrypted_at_rest(self):
        from django.db import connection

        self.client.post(self.url, registration_payload(), format="json")
        user = User.objects.get(email="newuser@example.com")

        # Bypass the ORM's field conversion (from_db_value would transparently
        # decrypt it) to inspect what is actually stored in the database.
        with connection.cursor() as cursor:
            cursor.execute("SELECT phone_number FROM accounts_user WHERE id = %s", [user.id])
            raw_value = cursor.fetchone()[0]

        self.assertNotEqual(raw_value, "+14155552671")
        self.assertEqual(user.phone_number, "+14155552671")

    def test_duplicate_email_rejected(self):
        self.client.post(self.url, registration_payload(), format="json")
        response = self.client.post(self.url, registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            self.url, registration_payload(confirm_password="Different!42"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_weak_password_rejected(self):
        response = self.client.post(
            self.url,
            registration_payload(password="password", confirm_password="password"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_phone_number_rejected(self):
        response = self.client.post(
            self.url, registration_payload(phone_number="not-a-phone"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_invalid_dropoff_location_rejected(self):
        response = self.client.post(
            self.url, registration_payload(dropoff_location="boston"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
