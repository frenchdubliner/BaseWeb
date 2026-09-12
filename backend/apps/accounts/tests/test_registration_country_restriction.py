from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.security.models import RegistrationAllowedCountry, RegistrationCountryRestriction

from .helpers import registration_payload


@override_settings(GEOIP_ENABLED=True)
class RegistrationCountryRestrictionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("register")

    @patch("apps.accounts.views.get_country_city", return_value=("FR", "Paris"))
    def test_registration_blocked_for_disallowed_country(self, _mock):
        restriction = RegistrationCountryRestriction.objects.create(enabled=True)
        RegistrationAllowedCountry.objects.create(restriction=restriction, country_code="US")

        response = self.client.post(self.url, registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.accounts.views.get_country_city", return_value=("US", "New York"))
    def test_registration_allowed_for_allowed_country(self, _mock):
        restriction = RegistrationCountryRestriction.objects.create(enabled=True)
        RegistrationAllowedCountry.objects.create(restriction=restriction, country_code="US")

        response = self.client.post(self.url, registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("apps.accounts.views.get_country_city", return_value=("FR", "Paris"))
    def test_disabled_restriction_allows_any_country(self, _mock):
        RegistrationCountryRestriction.objects.create(enabled=False)
        response = self.client.post(self.url, registration_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
