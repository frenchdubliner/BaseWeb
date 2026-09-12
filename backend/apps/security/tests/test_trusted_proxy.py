from django.test import RequestFactory, TestCase, override_settings

from apps.security.middleware import TrustedProxyMiddleware


class TrustedProxyMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = TrustedProxyMiddleware(get_response=lambda request: None)

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.1"])
    def test_forwarded_header_ignored_from_untrusted_peer(self):
        request = self.factory.get("/", REMOTE_ADDR="203.0.113.9", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.middleware(request)
        self.assertEqual(request.client_ip, "203.0.113.9")

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.1"])
    def test_forwarded_header_honoured_from_trusted_proxy(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1"
        )
        self.middleware(request)
        self.assertEqual(request.client_ip, "1.2.3.4")

    @override_settings(TRUSTED_PROXY_IPS=[])
    def test_no_trusted_proxies_configured_uses_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="203.0.113.9", HTTP_X_FORWARDED_FOR="1.2.3.4")
        self.middleware(request)
        self.assertEqual(request.client_ip, "203.0.113.9")
