from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.audit.models import AuditLog
from apps.listings.csv_import import TEMPLATE_CSV
from apps.listings.models import GameListing


class ReceivedFieldVisibilityTests(APITestCase):
    """`received` must never be visible to, or settable by, the listing's
    owner - only to admins, same as `printed`."""

    def setUp(self):
        cache.clear()
        self.owner = make_user(email="seller@example.com", is_active=True)
        login = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_default_is_false(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        self.assertFalse(listing.received)

    def test_received_not_in_create_response(self):
        payload = {"game_name": "Catan", "price": "25.00", "condition": "good", "received": True}
        response = self.client.post(reverse("game-listing-list"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn("received", response.data)
        listing = GameListing.objects.get(pk=response.data["id"])
        self.assertFalse(listing.received)

    def test_received_not_in_list_or_retrieve_response(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        response = self.client.get(reverse("game-listing-detail", args=[listing.pk]))
        self.assertNotIn("received", response.data)
        response = self.client.get(reverse("game-listing-list"))
        self.assertNotIn("received", response.data[0])

    def test_owner_cannot_set_received_via_update(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        response = self.client.patch(
            reverse("game-listing-detail", args=[listing.pk]), {"received": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertFalse(listing.received)

    def test_template_does_not_mention_received(self):
        self.assertNotIn("received", TEMPLATE_CSV.lower())

    def test_csv_with_received_column_is_ignored(self):
        import io

        content = "game_name,price,condition,received\nCatan,25.00,good,TRUE\n"
        upload = io.BytesIO(content.encode("utf-8"))
        upload.name = "games.csv"
        response = self.client.post(
            reverse("game-listing-bulk-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        listing = GameListing.objects.get(game_name="Catan")
        self.assertFalse(listing.received)


class AdminReceivedToggleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.owner = make_user(email="seller@example.com", is_active=True)

        login = self.client.post(
            reverse("login"), {"email": "admin@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        self.listing = GameListing.objects.create(
            owner=self.owner, game_name="Catan", price=25, condition="good", received=False
        )
        self.detail_url = reverse("admin-game-listing-detail", args=[self.listing.pk])

    def test_admin_sees_received_field(self):
        response = self.client.get(self.detail_url)
        self.assertFalse(response.data["received"])

    def test_admin_can_toggle_received_true(self):
        response = self.client.patch(self.detail_url, {"received": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["received"])
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.received)

    def test_admin_can_toggle_received_back_to_false(self):
        self.listing.received = True
        self.listing.save(update_fields=["received"])
        response = self.client.patch(self.detail_url, {"received": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertFalse(self.listing.received)

    def test_toggling_received_is_audited(self):
        self.client.patch(self.detail_url, {"received": True}, format="json")
        self.assertTrue(
            AuditLog.objects.filter(
                event_type=AuditLog.EventType.ADMIN_ACTION, target_user=self.owner
            ).exists()
        )

    def test_non_admin_cannot_toggle_received(self):
        login = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self.client.patch(self.detail_url, {"received": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_toggling_received_on_printed_listing_still_works(self):
        # received is independent of the printed lock - admin can always
        # edit printed listings, and this is a normal admin edit.
        self.listing.printed = True
        self.listing.save(update_fields=["printed"])
        response = self.client.patch(self.detail_url, {"received": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdminReceivedFilterTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.owner = make_user(email="seller@example.com", is_active=True)

        login = self.client.post(
            reverse("login"), {"email": "admin@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        self.received_listing = GameListing.objects.create(
            owner=self.owner, game_name="Catan", price=25, condition="good", received=True
        )
        self.unreceived_listing = GameListing.objects.create(
            owner=self.owner, game_name="Risk", price=5, condition="poor", received=False
        )
        self.list_url = reverse("admin-game-listing-list")

    def test_filter_by_received_true(self):
        response = self.client.get(self.list_url, {"received": "true"})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])

    def test_filter_by_received_false(self):
        response = self.client.get(self.list_url, {"received": "false"})
        self.assertEqual([item["game_name"] for item in response.data], ["Risk"])

    def test_no_received_filter_returns_both(self):
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 2)

    def test_received_and_printed_filters_combine(self):
        self.received_listing.printed = True
        self.received_listing.save(update_fields=["printed"])
        response = self.client.get(self.list_url, {"received": "true", "printed": "true"})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])
        response = self.client.get(self.list_url, {"received": "true", "printed": "false"})
        self.assertEqual(response.data, [])
