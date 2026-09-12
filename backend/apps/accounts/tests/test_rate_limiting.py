from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from .helpers import make_user, registration_payload


class AxesLockoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("login")
        make_user(email="locktarget@example.com", is_active=True)

    def test_account_locks_out_after_repeated_failures(self):
        for _ in range(5):
            response = self.client.post(
                self.login_url,
                {"email": "locktarget@example.com", "password": "WrongPass!1"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Even the correct password should now be rejected while locked out.
        response = self.client.post(
            self.login_url,
            {"email": "locktarget@example.com", "password": "Sup3rSecret!42"},
            format="json",
        )
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


class RegistrationThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("register")

    def test_registration_is_rate_limited(self):
        # ScopedRateThrottle reads its rates from a class attribute snapshotted
        # at import time, so override it directly rather than via
        # override_settings (which would not be picked up by the class).
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"register": "2/min"}):
            statuses = []
            for i in range(3):
                response = self.client.post(
                    self.url, registration_payload(email=f"throttle{i}@example.com"), format="json"
                )
                statuses.append(response.status_code)
        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, statuses)
