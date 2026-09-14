from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.audit.models import AuditLog

from .helpers import make_user


class AdminUserListTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.alice = make_user(
            email="alice@example.com",
            first_name="Alice",
            last_name="Anderson",
            phone_number="+14155552671",
        )
        self.bob = make_user(
            email="bob@example.com",
            first_name="Bob",
            last_name="Brown",
            phone_number="+442071838750",
        )

        self.list_url = reverse("admin-user-list")

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_forbidden(self):
        self._login("alice@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_all_users(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = {u["email"] for u in response.data}
        self.assertEqual(emails, {"admin@example.com", "alice@example.com", "bob@example.com"})

    def test_filter_by_email(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"email": "alice"})
        self.assertEqual([u["email"] for u in response.data], ["alice@example.com"])

    def test_filter_by_first_name(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"first_name": "bob"})
        self.assertEqual([u["email"] for u in response.data], ["bob@example.com"])

    def test_filter_by_last_name(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"last_name": "anderson"})
        self.assertEqual([u["email"] for u in response.data], ["alice@example.com"])

    def test_filter_by_phone_number(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"phone_number": "442071838750"})
        self.assertEqual([u["email"] for u in response.data], ["bob@example.com"])

    def test_combined_filters_are_anded(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"first_name": "alice", "last_name": "brown"})
        self.assertEqual(response.data, [])

    def test_clearing_filters_returns_full_list(self):
        self._login("admin@example.com")
        self.client.get(self.list_url, {"email": "alice"})
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 3)


class AdminUserUpdateTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.alice = make_user(email="alice@example.com", first_name="Alice", last_name="Anderson")
        self.detail_url = reverse("admin-user-detail", args=[self.alice.pk])

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_non_admin_cannot_update(self):
        self._login("alice@example.com")
        response = self.client.patch(self.detail_url, {"first_name": "Hacked"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_profile_fields(self):
        self._login("admin@example.com")
        response = self.client.patch(
            self.detail_url,
            {"first_name": "Alicia", "dropoff_location": "saugus"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.first_name, "Alicia")
        self.assertEqual(self.alice.dropoff_location, "saugus")

    def test_admin_can_manually_activate_a_user(self):
        pending = make_user(email="pending@example.com", is_active=False)
        self._login("admin@example.com")
        response = self.client.patch(
            reverse("admin-user-detail", args=[pending.pk]), {"is_active": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)

    def test_is_staff_is_not_editable_via_this_endpoint(self):
        self._login("admin@example.com")
        response = self.client.patch(self.detail_url, {"is_staff": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_staff)

    def test_update_is_audited(self):
        self._login("admin@example.com")
        self.client.patch(self.detail_url, {"first_name": "Alicia"}, format="json")
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ADMIN_ACTION, target_user=self.alice
            ).exists()
        )

    def test_duplicate_email_rejected(self):
        make_user(email="taken@example.com")
        self._login("admin@example.com")
        response = self.client.patch(self.detail_url, {"email": "taken@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
