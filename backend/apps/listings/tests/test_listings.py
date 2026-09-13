from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.models import GameListing


def listing_payload(**overrides):
    payload = {
        "game_name": "Catan",
        "price": "25.00",
        "condition": "very_good",
        "has_missing_pieces": False,
        "smoking_household": False,
        "musty_smell": False,
        "pet_exposure": "cat",
    }
    payload.update(overrides)
    return payload


class GameListingTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user(email="seller@example.com", is_active=True)
        self.other_user = make_user(email="other-seller@example.com", is_active=True)
        self.list_url = reverse("game-listing-list")

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def detail_url(self, pk):
        return reverse("game-listing-detail", args=[pk])

    def test_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unverified_user_cannot_access_listings(self):
        make_user(email="pending@example.com", is_active=False)
        self._login("pending@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_listing_sets_owner_automatically(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        listing = GameListing.objects.get(pk=response.data["id"])
        self.assertEqual(listing.owner, self.user)
        self.assertEqual(response.data["condition_description"], "Pieces punched, sorted, rarely or never played. No discernible wear.")

    def test_invalid_condition_rejected(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(condition="mint"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_pet_exposure_rejected(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(pet_exposure="hamster"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pet_exposure_optional(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(pet_exposure=""), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_negative_price_rejected(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(price="-5.00"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_returns_own_listings(self):
        GameListing.objects.create(owner=self.user, game_name="Mine", price=10, condition="good")
        GameListing.objects.create(owner=self.other_user, game_name="Not mine", price=10, condition="good")

        self._login("seller@example.com")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["game_name"] for item in response.data]
        self.assertEqual(names, ["Mine"])

    def test_owner_can_update_own_listing(self):
        listing = GameListing.objects.create(owner=self.user, game_name="Mine", price=10, condition="good")
        self._login("seller@example.com")
        response = self.client.patch(self.detail_url(listing.pk), {"price": "15.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listing.refresh_from_db()
        self.assertEqual(str(listing.price), "15.00")

    def test_owner_can_delete_own_listing(self):
        listing = GameListing.objects.create(owner=self.user, game_name="Mine", price=10, condition="good")
        self._login("seller@example.com")
        response = self.client.delete(self.detail_url(listing.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GameListing.objects.filter(pk=listing.pk).exists())

    def test_cannot_view_another_users_listing(self):
        listing = GameListing.objects.create(owner=self.other_user, game_name="Not mine", price=10, condition="good")
        self._login("seller@example.com")
        response = self.client.get(self.detail_url(listing.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_update_another_users_listing(self):
        listing = GameListing.objects.create(owner=self.other_user, game_name="Not mine", price=10, condition="good")
        self._login("seller@example.com")
        response = self.client.patch(self.detail_url(listing.pk), {"price": "999.00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        listing.refresh_from_db()
        self.assertEqual(str(listing.price), "10.00")

    def test_cannot_delete_another_users_listing(self):
        listing = GameListing.objects.create(owner=self.other_user, game_name="Not mine", price=10, condition="good")
        self._login("seller@example.com")
        response = self.client.delete(self.detail_url(listing.pk))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(GameListing.objects.filter(pk=listing.pk).exists())

    def test_missing_pieces_description_is_saved(self):
        self._login("seller@example.com")
        response = self.client.post(
            self.list_url,
            listing_payload(has_missing_pieces=True, missing_pieces_description="2 red meeples, 1 die"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["missing_pieces_description"], "2 red meeples, 1 die")

    def test_missing_pieces_description_cleared_when_unchecked(self):
        self._login("seller@example.com")
        response = self.client.post(
            self.list_url,
            listing_payload(has_missing_pieces=False, missing_pieces_description="should be dropped"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["missing_pieces_description"], "")

    def test_missing_pieces_description_over_64_chars_rejected(self):
        self._login("seller@example.com")
        response = self.client.post(
            self.list_url,
            listing_payload(has_missing_pieces=True, missing_pieces_description="x" * 65),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("missing_pieces_description", response.data)

    def test_comments_field_saved(self):
        self._login("seller@example.com")
        response = self.client.post(
            self.list_url, listing_payload(comments="Great condition, smoke-free home"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["comments"], "Great condition, smoke-free home")

    def test_comments_over_64_chars_rejected(self):
        self._login("seller@example.com")
        response = self.client.post(self.list_url, listing_payload(comments="x" * 65), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comments", response.data)
