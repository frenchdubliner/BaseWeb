from django.test import TestCase
from django.urls import reverse


class SecurityHeadersTests(TestCase):
    def test_security_headers_present_on_api_responses(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.get("X-Frame-Options"), "DENY")
        self.assertIn("Content-Security-Policy", response)
