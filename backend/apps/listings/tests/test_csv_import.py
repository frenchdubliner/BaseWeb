import io

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.csv_import import TEMPLATE_CSV
from apps.listings.models import GameListing


def csv_file(content, name="games.csv"):
    return io.BytesIO(content.encode("utf-8")), name


class CSVTemplateDownloadTests(APITestCase):
    def setUp(self):
        cache.clear()
        make_user(email="seller@example.com", is_active=True)
        response = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_template_download_requires_auth(self):
        self.client.credentials()
        response = self.client.get(reverse("game-listing-csv-template"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_template_downloads_as_csv_attachment(self):
        response = self.client.get(reverse("game-listing-csv-template"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("game_listings_template.csv", response["Content-Disposition"])

    def test_template_content_is_actually_importable(self):
        """The example file we tell users to download must itself import cleanly."""
        response = self.client.get(reverse("game-listing-csv-template"))
        content = response.content.decode()
        self.assertEqual(content, TEMPLATE_CSV)

        upload = io.BytesIO(content.encode("utf-8"))
        upload.name = "template.csv"
        upload_response = self.client.post(
            reverse("game-listing-bulk-upload"), {"file": upload}, format="multipart"
        )
        self.assertEqual(upload_response.status_code, status.HTTP_200_OK, upload_response.data)
        self.assertEqual(upload_response.data["error_count"], 0)
        self.assertEqual(upload_response.data["created_count"], 10)

        pandemic = GameListing.objects.get(game_name="Pandemic")
        self.assertEqual(pandemic.missing_pieces_description, "Missing 2 blue infection cubes")
        self.assertEqual(pandemic.comments, "Ask about bundle discount")

        monopoly = GameListing.objects.get(game_name__startswith="Monopoly")
        self.assertEqual(monopoly.missing_pieces_description, "Missing dog token, 3 houses")

        catan = GameListing.objects.get(game_name="Catan")
        self.assertEqual(catan.missing_pieces_description, "")
        self.assertEqual(catan.comments, "Great starter game - highly recommend")


class CSVBulkUploadTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user(email="seller@example.com", is_active=True)
        self.url = reverse("game-listing-bulk-upload")
        response = self.client.post(
            reverse("login"), {"email": "seller@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def _upload(self, content):
        data, name = csv_file(content)
        data.name = name
        return self.client.post(self.url, {"file": data}, format="multipart")

    def test_requires_authentication(self):
        self.client.credentials()
        data, name = csv_file("game_name,price,condition\nCatan,25,very_good\n")
        data.name = name
        response = self.client.post(self.url, {"file": data}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unverified_user_blocked(self):
        make_user(email="pending@example.com", is_active=False)
        login = self.client.post(
            reverse("login"), {"email": "pending@example.com", "password": "Sup3rSecret!42"}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        response = self._upload("game_name,price,condition\nCatan,25,very_good\n")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_file_provided(self):
        response = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_non_csv_extension(self):
        data = io.BytesIO(b"not a csv")
        data.name = "games.txt"
        response = self.client.post(self.url, {"file": data}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_rows_are_created_for_the_uploading_user(self):
        content = (
            "game_name,price,condition,has_missing_pieces,smoking_household,musty_smell,pet_exposure\n"
            "Catan,25.00,very_good,FALSE,FALSE,FALSE,cat\n"
            "Risk,5.00,poor,TRUE,FALSE,FALSE,\n"
        )
        response = self._upload(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["created_count"], 2)
        self.assertEqual(response.data["error_count"], 0)
        self.assertEqual(GameListing.objects.filter(owner=self.user).count(), 2)
        catan = GameListing.objects.get(owner=self.user, game_name="Catan")
        self.assertEqual(catan.pet_exposure, "cat")
        self.assertTrue(GameListing.objects.get(owner=self.user, game_name="Risk").has_missing_pieces)

    def test_comment_lines_and_blank_lines_are_ignored(self):
        content = (
            "# this is a comment\n"
            "\n"
            "game_name,price,condition\n"
            "# another comment\n"
            "Catan,25.00,very_good\n"
        )
        response = self._upload(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["created_count"], 1)

    def test_human_readable_condition_label_is_accepted(self):
        content = "game_name,price,condition\nCatan,25.00,Very Good\n"
        response = self._upload(content)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(GameListing.objects.get(game_name="Catan").condition, "very_good")

    def test_partial_failure_reports_row_errors_but_still_imports_valid_rows(self):
        content = (
            "game_name,price,condition\n"
            "Catan,25.00,very_good\n"
            "Bad Game,not-a-number,very_good\n"
            "Another Bad,10.00,not_a_real_condition\n"
        )
        response = self._upload(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(response.data["error_count"], 2)
        rows_with_errors = {err["row"] for err in response.data["errors"]}
        self.assertEqual(rows_with_errors, {2, 3})
        self.assertEqual(GameListing.objects.filter(owner=self.user).count(), 1)

    def test_missing_required_column_reported_as_row_error(self):
        content = "game_name,price\nCatan,25.00\n"
        response = self._upload(content)
        self.assertEqual(response.data["created_count"], 0)
        self.assertEqual(response.data["error_count"], 1)
        self.assertIn("condition", response.data["errors"][0]["errors"])

    def test_boolean_variants_are_parsed(self):
        content = (
            "game_name,price,condition,has_missing_pieces\n"
            "A,1,good,true\n"
            "B,1,good,Yes\n"
            "C,1,good,1\n"
            "D,1,good,false\n"
            "E,1,good,\n"
        )
        response = self._upload(content)
        self.assertEqual(response.data["created_count"], 5)
        flags = {
            listing.game_name: listing.has_missing_pieces
            for listing in GameListing.objects.filter(owner=self.user)
        }
        self.assertEqual(flags, {"A": True, "B": True, "C": True, "D": False, "E": False})

    def test_too_many_rows_rejected(self):
        header = "game_name,price,condition\n"
        rows = "".join(f"Game {i},1.00,good\n" for i in range(501))
        response = self._upload(header + rows)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(GameListing.objects.filter(owner=self.user).count(), 0)

    def test_uploaded_listings_are_scoped_to_uploading_user_only(self):
        other_user = make_user(email="other@example.com", is_active=True)
        self._upload("game_name,price,condition\nCatan,25.00,very_good\n")
        self.assertEqual(GameListing.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(GameListing.objects.filter(owner=other_user).count(), 0)
