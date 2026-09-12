from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.security.models import GeoRestrictionCountry, GeoRestrictionSettings


@override_settings(GEOIP_ENABLED=True)
class GeoRestrictionMiddlewareTests(TestCase):
    def setUp(self):
        self.url = reverse("register")

    @patch("apps.security.geoip.get_country_city", return_value=("FR", "Paris"))
    def test_whitelist_blocks_disallowed_country(self, _mock):
        config = GeoRestrictionSettings.objects.create(mode="whitelist")
        GeoRestrictionCountry.objects.create(settings=config, country_code="US")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(event_type=AuditLog.EventType.GEO_BLOCK).exists())

    @patch("apps.security.geoip.get_country_city", return_value=("US", "New York"))
    def test_whitelist_allows_allowed_country(self, _mock):
        config = GeoRestrictionSettings.objects.create(mode="whitelist")
        GeoRestrictionCountry.objects.create(settings=config, country_code="US")

        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 403)

    @patch("apps.security.geoip.get_country_city", return_value=("CN", "Beijing"))
    def test_blacklist_blocks_listed_country(self, _mock):
        config = GeoRestrictionSettings.objects.create(mode="blacklist")
        GeoRestrictionCountry.objects.create(settings=config, country_code="CN")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    @patch("apps.security.geoip.get_country_city", return_value=("CN", "Beijing"))
    def test_disabled_mode_does_not_block(self, _mock):
        GeoRestrictionSettings.objects.create(mode="disabled")
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 403)
