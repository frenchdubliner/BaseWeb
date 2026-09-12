from django.test import TestCase
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.security.models import IPRestrictionEntry, IPRestrictionSettings


class IPRestrictionMiddlewareTests(TestCase):
    def setUp(self):
        self.url = reverse("register")

    def test_blacklist_blocks_listed_ip(self):
        config = IPRestrictionSettings.objects.create(mode="blacklist")
        IPRestrictionEntry.objects.create(settings=config, ip_or_cidr="9.9.9.9")

        response = self.client.get(self.url, REMOTE_ADDR="9.9.9.9")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(event_type=AuditLog.EventType.IP_BLOCK).exists())

    def test_blacklist_allows_unlisted_ip(self):
        config = IPRestrictionSettings.objects.create(mode="blacklist")
        IPRestrictionEntry.objects.create(settings=config, ip_or_cidr="9.9.9.9")

        response = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")
        self.assertNotEqual(response.status_code, 403)

    def test_whitelist_blocks_unlisted_ip(self):
        config = IPRestrictionSettings.objects.create(mode="whitelist")
        IPRestrictionEntry.objects.create(settings=config, ip_or_cidr="8.8.8.8")

        response = self.client.get(self.url, REMOTE_ADDR="9.9.9.9")
        self.assertEqual(response.status_code, 403)

    def test_whitelist_allows_listed_ip(self):
        config = IPRestrictionSettings.objects.create(mode="whitelist")
        IPRestrictionEntry.objects.create(settings=config, ip_or_cidr="8.8.8.8")

        response = self.client.get(self.url, REMOTE_ADDR="8.8.8.8")
        self.assertNotEqual(response.status_code, 403)

    def test_cidr_range_matches(self):
        config = IPRestrictionSettings.objects.create(mode="blacklist")
        IPRestrictionEntry.objects.create(settings=config, ip_or_cidr="203.0.113.0/24")

        response = self.client.get(self.url, REMOTE_ADDR="203.0.113.42")
        self.assertEqual(response.status_code, 403)

    def test_disabled_mode_does_not_block(self):
        IPRestrictionSettings.objects.create(mode="disabled")
        response = self.client.get(self.url, REMOTE_ADDR="9.9.9.9")
        self.assertNotEqual(response.status_code, 403)
