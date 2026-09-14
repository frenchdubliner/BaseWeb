from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.audit.models import AuditLog
from apps.listings.models import GameListing


class AdminGameListingListTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

        self.alice = make_user(
            email="alice@example.com", first_name="Alice", last_name="Anderson", dropoff_location="norton"
        )
        self.bob = make_user(
            email="bob@example.com", first_name="Bob", last_name="Brown", dropoff_location="saugus"
        )

        self.catan = GameListing.objects.create(owner=self.alice, game_name="Catan", price=25, condition="good")
        self.risk = GameListing.objects.create(owner=self.bob, game_name="Risk", price=5, condition="poor")

        self.list_url = reverse("admin-game-listing-list")

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def detail_url(self, pk):
        return reverse("admin-game-listing-detail", args=[pk])

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_forbidden(self):
        self._login("alice@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_sees_every_users_listings(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {item["game_name"] for item in response.data}
        self.assertEqual(names, {"Catan", "Risk"})
        catan_row = next(item for item in response.data if item["game_name"] == "Catan")
        self.assertEqual(catan_row["owner_email"], "alice@example.com")

    def test_filter_by_id(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"id": self.catan.pk})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])

    def test_filter_by_non_numeric_id_returns_empty(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"id": "not-a-number"})
        self.assertEqual(response.data, [])

    def test_filter_by_owner_email(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"email": "bob"})
        self.assertEqual([item["game_name"] for item in response.data], ["Risk"])

    def test_filter_by_owner_first_name(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"first_name": "alice"})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])

    def test_filter_by_owner_last_name(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"last_name": "brown"})
        self.assertEqual([item["game_name"] for item in response.data], ["Risk"])

    def test_filter_by_dropoff_location(self):
        self._login("admin@example.com")
        response = self.client.get(self.list_url, {"dropoff_location": "norton"})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])

    def test_admin_can_update_any_listing(self):
        self._login("admin@example.com")
        response = self.client.patch(self.detail_url(self.catan.pk), {"price": "99.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.catan.refresh_from_db()
        self.assertEqual(str(self.catan.price), "99.00")
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ADMIN_ACTION, target_user=self.alice
            ).exists()
        )

    def test_admin_cannot_reassign_owner(self):
        self._login("admin@example.com")
        response = self.client.patch(self.detail_url(self.catan.pk), {"owner": self.bob.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.catan.refresh_from_db()
        self.assertEqual(self.catan.owner, self.alice)

    def test_admin_can_delete_any_listing(self):
        self._login("admin@example.com")
        response = self.client.delete(self.detail_url(self.risk.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GameListing.objects.filter(pk=self.risk.pk).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ADMIN_ACTION, target_user=self.bob
            ).exists()
        )

    def test_non_admin_cannot_delete(self):
        self._login("alice@example.com")
        response = self.client.delete(self.detail_url(self.risk.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(GameListing.objects.filter(pk=self.risk.pk).exists())
