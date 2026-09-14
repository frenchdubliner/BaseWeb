from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.tests.helpers import make_user
from apps.listings.models import GameListing
from apps.listings.pdf import PAGE_HEIGHT, PAGE_WIDTH, _fit_font_size, _wrap_text, generate_price_tag_pdf


class WrapTextTests(APITestCase):
    def test_short_text_is_one_line(self):
        self.assertEqual(_wrap_text("Catan", "Helvetica", 10, 100), ["Catan"])

    def test_long_text_wraps_to_multiple_lines(self):
        text = "This is a very long game name that will not fit on one line at all"
        lines = _wrap_text(text, "Helvetica", 10, 60)
        self.assertGreater(len(lines), 1)
        # Every line must actually fit within the given width.
        from reportlab.pdfbase.pdfmetrics import stringWidth

        for line in lines:
            self.assertLessEqual(stringWidth(line, "Helvetica", 10), 60)

    def test_empty_text_returns_one_empty_line(self):
        self.assertEqual(_wrap_text("", "Helvetica", 10, 100), [""])

    def test_single_word_wider_than_max_width_is_clamped_not_overflowed(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth

        # A real bug caught by visual inspection: one long unbroken "word"
        # (no spaces) was placed on its own line with no width check,
        # overflowing straight off the fixed-size page.
        word = "A" * 60
        lines = _wrap_text(word, "Helvetica-Bold", 13, 128)
        for line in lines:
            self.assertLessEqual(stringWidth(line, "Helvetica-Bold", 13), 128)


class FitFontSizeTests(APITestCase):
    def test_short_text_keeps_start_size(self):
        size = _fit_font_size("Catan", "Helvetica-Bold", 13, 8, 128, 2)
        self.assertEqual(size, 13)

    def test_long_text_shrinks_to_fit_max_lines(self):
        text = "An Extremely Long Board Game Title That Keeps Going And Going"
        size = _fit_font_size(text, "Helvetica-Bold", 13, 8, 128, 2)
        self.assertLess(size, 13)
        self.assertGreaterEqual(size, 8)

    def test_never_goes_below_min_size(self):
        text = "x " * 200
        size = _fit_font_size(text, "Helvetica-Bold", 13, 8, 128, 2)
        self.assertEqual(size, 8)


class GeneratePriceTagPdfTests(APITestCase):
    def setUp(self):
        self.owner = make_user(email="seller@example.com", is_active=True)

    def test_minimal_listing_produces_valid_pdf(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Catan", price=25, condition="good")
        pdf_bytes = generate_price_tag_pdf(listing, "PAXE2026")
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 500)

    def test_listing_with_every_flag_set_does_not_crash(self):
        listing = GameListing.objects.create(
            owner=self.owner,
            game_name="Gloomhaven: Jaws of the Lion Collector's Edition",
            price=199.99,
            condition="fair",
            has_missing_pieces=True,
            missing_pieces_description="x" * 64,
            smoking_household=True,
            musty_smell=True,
            pet_exposure="multiple",
            comments="y" * 64,
        )
        pdf_bytes = generate_price_tag_pdf(listing, "PAXE2026")
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_unbroken_overlong_game_name_does_not_crash(self):
        # Regression test for the bug fixed in _wrap_text/_clamp_to_width:
        # a single word with no spaces used to be placed on its own line
        # with no width check at all, overflowing off the page.
        listing = GameListing.objects.create(owner=self.owner, game_name="A" * 60, price=1, condition="good")
        pdf_bytes = generate_price_tag_pdf(listing, "PAXE2026")
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_very_long_convention_name_does_not_crash(self):
        listing = GameListing.objects.create(owner=self.owner, game_name="Risk", price=5, condition="poor")
        pdf_bytes = generate_price_tag_pdf(listing, "A" * 60)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_page_size_is_2x3_inches(self):
        self.assertEqual(PAGE_WIDTH, 144)
        self.assertEqual(PAGE_HEIGHT, 216)


class AdminGamePrintEndpointTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = make_user(email="admin@example.com", is_active=True)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.regular = make_user(email="regular@example.com", is_active=True)
        self.owner = make_user(email="owner@example.com", is_active=True)
        self.listing = GameListing.objects.create(
            owner=self.owner, game_name="Catan", price=25, condition="very_good"
        )
        self.print_url = reverse("admin-game-listing-print", args=[self.listing.pk])

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_requires_authentication(self):
        response = self.client.get(self.print_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_forbidden(self):
        self._login("regular@example.com")
        response = self.client.get(self.print_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_gets_pdf_download(self):
        self._login("admin@example.com")
        response = self.client.get(self.print_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(f"game-{self.listing.pk}-price-tag.pdf", response["Content-Disposition"])
        content = b"".join(response.streaming_content) if response.streaming else response.content
        self.assertTrue(content.startswith(b"%PDF"))

    def test_nonexistent_listing_404(self):
        self._login("admin@example.com")
        response = self.client.get(reverse("admin-game-listing-print", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_uses_current_convention_name(self):
        from apps.convention.models import ConventionSettings

        convention = ConventionSettings.load()
        convention.name = "GenCon2099"
        convention.save()

        self._login("admin@example.com")
        response = self.client.get(self.print_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
