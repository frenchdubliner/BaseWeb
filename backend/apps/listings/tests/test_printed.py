from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.csv_import import TEMPLATE_CSV
from apps.listings.models import GameListing


class PrintedFieldVisibilityTests(APITestCase):
    """The `printed` attribute must never be visible to, or settable by,
    the listing's owner - only to admins."""

    def setUp(self):
        cache.clear()
        self.owner = make_user(email="seller@example.com", is_active=True)
        login = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def _payload(self, **overrides):
        payload = {
            "game_name": "Catan",
            "price": "25.00",
            "condition": "good",
        }
        payload.update(overrides)
        return payload

    def test_default_is_false(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        self.assertFalse(listing.printed)

    def test_printed_not_in_create_response(self):
        response = self.client.post(reverse("game-listing-list"), self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertNotIn("printed", response.data)

    def test_printed_not_in_retrieve_response(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        response = self.client.get(reverse("game-listing-detail", args=[listing.pk]))
        self.assertNotIn("printed", response.data)

    def test_printed_not_in_list_response(self):
        GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        response = self.client.get(reverse("game-listing-list"))
        self.assertNotIn("printed", response.data[0])

    def test_cannot_set_printed_via_create(self):
        response = self.client.post(
            reverse("game-listing-list"), self._payload(printed=True), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        listing = GameListing.objects.get(pk=response.data["id"])
        self.assertFalse(listing.printed)

    def test_cannot_set_printed_via_update(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        response = self.client.patch(
            reverse("game-listing-detail", args=[listing.pk]), {"printed": True}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertFalse(listing.printed)


class PrintedLocksOwnerEditingTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user(email="seller@example.com", is_active=True)
        login = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.listing = GameListing.objects.create(
            owner=self.owner, game_name="Catan", price=25, condition="good", printed=True
        )
        self.detail_url = reverse("game-listing-detail", args=[self.listing.pk])

    def test_owner_cannot_update_printed_listing(self):
        response = self.client.patch(self.detail_url, {"price": "1.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("no longer be edited", response.data["detail"].lower())
        self.listing.refresh_from_db()
        self.assertEqual(str(self.listing.price), "25.00")

    def test_rejection_message_never_says_printed(self):
        # The word "printed" - like the attribute itself - must never reach
        # the owner, even in an error message explaining a 403.
        update_response = self.client.patch(self.detail_url, {"price": "1.00"}, format="json")
        self.assertNotIn("printed", update_response.data["detail"].lower())

        delete_response = self.client.delete(self.detail_url)
        self.assertNotIn("printed", delete_response.data["detail"].lower())

    def test_owner_cannot_delete_printed_listing(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("no longer be deleted", response.data["detail"].lower())
        self.assertTrue(GameListing.objects.filter(pk=self.listing.pk).exists())

    def test_owner_can_still_view_printed_listing(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_can_edit_is_false_for_printed_listing(self):
        response = self.client.get(self.detail_url)
        self.assertFalse(response.data["can_edit"])

    def test_can_edit_is_true_for_unprinted_listing(self):
        unprinted = GameListing.objects.create(
            owner=self.owner, game_name="Risk", price=5, condition="poor", printed=False
        )
        response = self.client.get(reverse("game-listing-detail", args=[unprinted.pk]))
        self.assertTrue(response.data["can_edit"])

    def test_can_edit_appears_in_list_response(self):
        response = self.client.get(reverse("game-listing-list"))
        by_name = {item["game_name"]: item["can_edit"] for item in response.data}
        self.assertEqual(by_name, {"Catan": False})

    def test_owner_can_still_edit_unprinted_listing(self):
        unprinted = GameListing.objects.create(
            owner=self.owner, game_name="Risk", price=5, condition="poor", printed=False
        )
        response = self.client.patch(
            reverse("game-listing-detail", args=[unprinted.pk]), {"price": "1.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PrintedCsvImportTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user(email="seller@example.com", is_active=True)
        login = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_template_does_not_mention_printed(self):
        self.assertNotIn("printed", TEMPLATE_CSV.lower())

    def test_csv_with_printed_column_is_ignored(self):
        import io

        content = "game_name,price,condition,printed\nCatan,25.00,good,TRUE\n"
        upload = io.BytesIO(content.encode("utf-8"))
        upload.name = "games.csv"
        response = self.client.post(
            reverse("game-listing-bulk-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["created_count"], 1)
        listing = GameListing.objects.get(game_name="Catan")
        self.assertFalse(listing.printed)


class AdminPrintedVisibilityAndFilterTests(APITestCase):
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

        self.printed_listing = GameListing.objects.create(
            owner=self.owner, game_name="Catan", price=25, condition="good", printed=True
        )
        self.unprinted_listing = GameListing.objects.create(
            owner=self.owner, game_name="Risk", price=5, condition="poor", printed=False
        )

    def test_admin_sees_printed_field(self):
        response = self.client.get(reverse("admin-game-listing-list"))
        by_name = {item["game_name"]: item["printed"] for item in response.data}
        self.assertEqual(by_name, {"Catan": True, "Risk": False})

    def test_admin_cannot_set_printed_via_edit(self):
        response = self.client.patch(
            reverse("admin-game-listing-detail", args=[self.unprinted_listing.pk]),
            {"printed": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unprinted_listing.refresh_from_db()
        self.assertFalse(self.unprinted_listing.printed)

    def test_admin_can_edit_printed_listing(self):
        response = self.client.patch(
            reverse("admin-game-listing-detail", args=[self.printed_listing.pk]),
            {"price": "99.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_admin_can_delete_printed_listing(self):
        response = self.client.delete(reverse("admin-game-listing-detail", args=[self.printed_listing.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_by_printed_true(self):
        response = self.client.get(reverse("admin-game-listing-list"), {"printed": "true"})
        self.assertEqual([item["game_name"] for item in response.data], ["Catan"])

    def test_filter_by_printed_false(self):
        response = self.client.get(reverse("admin-game-listing-list"), {"printed": "false"})
        self.assertEqual([item["game_name"] for item in response.data], ["Risk"])

    def test_no_printed_filter_returns_both(self):
        response = self.client.get(reverse("admin-game-listing-list"))
        self.assertEqual(len(response.data), 2)


class PrintActionsSetPrintedTrueTests(APITestCase):
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
            owner=self.owner, game_name="Catan", price=25, condition="good", printed=False
        )

    def test_single_print_marks_printed(self):
        self.assertFalse(self.listing.printed)
        response = self.client.get(reverse("admin-game-listing-print", args=[self.listing.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        self.assertTrue(self.listing.printed)

    def test_print_all_marks_all_matching_printed(self):
        other = GameListing.objects.create(
            owner=self.owner, game_name="Risk", price=5, condition="poor", printed=False
        )
        response = self.client.get(reverse("admin-game-listing-print-all"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing.refresh_from_db()
        other.refresh_from_db()
        self.assertTrue(self.listing.printed)
        self.assertTrue(other.printed)

    def test_reprinting_already_printed_listing_still_works(self):
        self.listing.printed = True
        self.listing.save(update_fields=["printed"])
        response = self.client.get(reverse("admin-game-listing-print", args=[self.listing.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
