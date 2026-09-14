from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.audit.models import AuditLog
from apps.convention.models import ConventionSettings, DEFAULT_CONVENTION_NAME


class ConventionSettingsTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.regular = make_user(email="regular@example.com", is_active=True)
        self.url = reverse("convention-settings")

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_forbidden(self):
        self._login("regular@example.com")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_default_name_before_any_change(self):
        self.assertEqual(ConventionSettings.objects.count(), 0)
        self._login("admin@example.com")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "PAXE2026")
        self.assertEqual(DEFAULT_CONVENTION_NAME, "PAXE2026")
        # Accessing it materializes the singleton row.
        self.assertEqual(ConventionSettings.objects.count(), 1)

    def test_admin_can_update_name(self):
        self._login("admin@example.com")
        response = self.client.patch(self.url, {"name": "PAXE2027"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["name"], "PAXE2027")

        get_response = self.client.get(self.url)
        self.assertEqual(get_response.data["name"], "PAXE2027")

    def test_there_is_only_ever_one_row(self):
        self._login("admin@example.com")
        self.client.patch(self.url, {"name": "First"}, format="json")
        self.client.patch(self.url, {"name": "Second"}, format="json")
        self.assertEqual(ConventionSettings.objects.count(), 1)
        self.assertEqual(ConventionSettings.objects.first().name, "Second")

    def test_non_admin_cannot_update(self):
        self._login("regular@example.com")
        response = self.client.patch(self.url, {"name": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_blank_name_rejected(self):
        self._login("admin@example.com")
        response = self.client.patch(self.url, {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_is_audited(self):
        self._login("admin@example.com")
        self.client.patch(self.url, {"name": "PAXE2027"}, format="json")
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ADMIN_ACTION, actor=self.admin
            ).exists()
        )

    def test_no_op_update_not_audited(self):
        self._login("admin@example.com")
        self.client.get(self.url)  # materialize with default name
        AuditLog.objects.all().delete()
        self.client.patch(self.url, {"name": "PAXE2026"}, format="json")
        self.assertFalse(AuditLog.objects.filter(event_type=AuditLog.EventType.ADMIN_ACTION).exists())
