import csv
import io

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.models import GameListing


class ExportCsvTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.regular = make_user(email="regular@example.com", is_active=True)

        self.alice = make_user(
            email="alice@example.com", first_name="Alice", last_name="Anderson", dropoff_location="norton"
        )
        self.bob = make_user(
            email="bob@example.com", first_name="Bob", last_name="Brown", dropoff_location="saugus"
        )
        self.catan = GameListing.objects.create(owner=self.alice, game_name="Catan", price=25, condition="good")
        self.risk = GameListing.objects.create(owner=self.bob, game_name="Risk", price=5, condition="poor")

        self.url = reverse("admin-game-listing-export")

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

    def test_exports_all_listings_as_csv(self):
        self._login("admin@example.com")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("games-export.csv", response["Content-Disposition"])

        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))
        self.assertEqual(len(rows), 2)
        game_names = {row["game_name"] for row in rows}
        self.assertEqual(game_names, {"Catan", "Risk"})

    def test_respects_filters(self):
        self._login("admin@example.com")
        response = self.client.get(self.url, {"dropoff_location": "saugus"})
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))
        self.assertEqual([row["game_name"] for row in rows], ["Risk"])

    def test_includes_admin_only_columns(self):
        self.catan.printed = True
        self.catan.save(update_fields=["printed"])
        self.client.post(reverse("login"), {"email": "admin@example.com", "password": "Sup3rSecret!42"}, format="json")
        self._login("admin@example.com")
        self.client.patch(
            reverse("admin-game-listing-detail", args=[self.catan.pk]), {"received": True}, format="json"
        )
        response = self.client.get(self.url)
        rows = {row["game_name"]: row for row in csv.DictReader(io.StringIO(response.content.decode("utf-8")))}

        self.assertEqual(rows["Catan"]["owner_email"], "alice@example.com")
        self.assertEqual(rows["Catan"]["owner_first_name"], "Alice")
        self.assertEqual(rows["Catan"]["printed"], "True")
        self.assertEqual(rows["Catan"]["received"], "True")
        self.assertNotEqual(rows["Catan"]["received_at"], "")
        self.assertEqual(rows["Catan"]["received_by"], "Jane Doe")

    def test_owner_never_exposed_to_this_endpoint(self):
        self._login("alice@example.com")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_matches_still_returns_header_only_csv(self):
        self._login("admin@example.com")
        response = self.client.get(self.url, {"email": "nobody@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8"))))
        self.assertEqual(rows, [])
