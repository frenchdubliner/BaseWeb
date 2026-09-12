from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import make_user


class ProfileAuthorizationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner = make_user(email="owner@example.com")
        self.other = make_user(email="other@example.com")
        self.admin = make_user(email="admin@example.com")
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])

    def _login(self, email, password="Sup3rSecret!42"):
        response = self.client.post(reverse("login"), {"email": email, "password": password}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_returns_only_the_authenticated_users_data(self):
        self._login("owner@example.com")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "owner@example.com")

    def test_non_admin_cannot_view_another_users_profile(self):
        self._login("other@example.com")
        response = self.client.get(reverse("user-admin-detail", args=[self.owner.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_view_another_users_profile(self):
        self._login("admin@example.com")
        response = self.client.get(reverse("user-admin-detail", args=[self.owner.pk]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "owner@example.com")

    def test_unauthenticated_request_to_admin_endpoint_denied(self):
        response = self.client.get(reverse("user-admin-detail", args=[self.owner.pk]))
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
