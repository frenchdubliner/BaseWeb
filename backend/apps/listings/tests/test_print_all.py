from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.models import GameListing
from apps.listings.pdf import MAX_PRINT_ALL


class PrintAllTests(APITestCase):
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

        self.url = reverse("admin-game-listing-print-all")

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

    def test_prints_all_when_no_filter_applied(self):
        self._login("admin@example.com")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("price-tags.pdf", response["Content-Disposition"])
        content = response.content
        self.assertTrue(content.startswith(b"%PDF"))
        # One page per listing - reportlab records page count in /Count.
        self.assertIn(b"/Count 2", content)

    def test_respects_filters(self):
        self._login("admin@example.com")
        response = self.client.get(self.url, {"dropoff_location": "saugus"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"/Count 1", response.content)

    def test_no_matches_returns_400_not_empty_pdf(self):
        self._login("admin@example.com")
        response = self.client.get(self.url, {"email": "nobody@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_too_many_matches_rejected(self):
        self._login("admin@example.com")
        with patch("apps.listings.views.MAX_PRINT_ALL", 1):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Narrow your filters", response.data["detail"])

    def test_route_does_not_shadow_detail_route(self):
        # Regression guard: "print-all" as a list action must be registered
        # before the "<pk>/" detail route, or it would be swallowed as if
        # "print-all" were an ID.
        self._login("admin@example.com")
        detail_response = self.client.get(reverse("admin-game-listing-detail", args=[self.catan.pk]))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
