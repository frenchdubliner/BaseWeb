import ipaddress
import logging

from django.conf import settings
from django.http import JsonResponse

from apps.security.utils import get_client_ip, ip_in_list, ip_matches

logger = logging.getLogger("apps.security")


class TrustedProxyMiddleware:
    """
    Resolves the real client IP. X-Forwarded-For is only honoured when the
    immediate connecting peer (REMOTE_ADDR) is a configured trusted proxy;
    otherwise REMOTE_ADDR is used as-is. This prevents IP spoofing via
    forged headers from untrusted clients.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        remote_addr = request.META.get("REMOTE_ADDR", "")
        client_ip = remote_addr

        # Entries may be exact IPs or CIDR ranges (e.g. a Docker network
        # subnet, since a reverse proxy container's address is not fixed).
        trusted_proxies = getattr(settings, "TRUSTED_PROXY_IPS", [])
        if trusted_proxies and any(ip_matches(remote_addr, entry) for entry in trusted_proxies):
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if forwarded_for:
                # left-most entry is the original client
                candidate = forwarded_for.split(",")[0].strip()
                try:
                    ipaddress.ip_address(candidate)
                    client_ip = candidate
                except ValueError:
                    pass

        request.client_ip = client_ip
        return self.get_response(request)


class IPRestrictionMiddleware:
    """Enforces site-wide IP whitelist/blacklist rules before authentication."""

    EXEMPT_PREFIXES = ()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.security.models import IPRestrictionSettings

        try:
            config = IPRestrictionSettings.objects.prefetch_related("entries").first()
        except Exception:
            config = None

        if config and config.mode != "disabled":
            ip = get_client_ip(request)
            entries = [e.ip_or_cidr for e in config.entries.all()]
            matched = ip_in_list(ip, entries)

            blocked = (config.mode == "whitelist" and not matched) or (
                config.mode == "blacklist" and matched
            )
            if blocked:
                self._log_block(request, ip)
                return JsonResponse(
                    {"detail": "Access denied from your network."}, status=403
                )

        return self.get_response(request)

    @staticmethod
    def _log_block(request, ip):
        from apps.audit.models import AuditLog

        logger.warning("Blocked request from restricted IP %s", ip)
        AuditLog.objects.create(
            event_type=AuditLog.EventType.IP_BLOCK,
            ip_address=ip,
            metadata={"path": request.path, "method": request.method},
        )


class GeoRestrictionMiddleware:
    """Enforces site-wide country whitelist/blacklist rules via GeoIP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.security.models import GeoRestrictionSettings

        if not getattr(settings, "GEOIP_ENABLED", False):
            return self.get_response(request)

        try:
            config = GeoRestrictionSettings.objects.prefetch_related("countries").first()
        except Exception:
            config = None

        if config and config.mode != "disabled":
            from apps.security.geoip import get_country_city

            ip = get_client_ip(request)
            country, _city = get_country_city(ip)
            countries = {c.country_code for c in config.countries.all()}

            if country:
                blocked = (config.mode == "whitelist" and country not in countries) or (
                    config.mode == "blacklist" and country in countries
                )
                if blocked:
                    self._log_block(request, ip, country)
                    return JsonResponse(
                        {"detail": "Access denied from your region."}, status=403
                    )

        return self.get_response(request)

    @staticmethod
    def _log_block(request, ip, country):
        from apps.audit.models import AuditLog

        logger.warning("Blocked request from restricted country %s (%s)", country, ip)
        AuditLog.objects.create(
            event_type=AuditLog.EventType.GEO_BLOCK,
            ip_address=ip,
            metadata={"path": request.path, "method": request.method, "country": country},
        )


class AdminAccessMiddleware:
    """Optional IP whitelist for the (obfuscated) Django admin panel."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            from apps.security.models import AdminSecuritySettings

            try:
                config = AdminSecuritySettings.objects.prefetch_related("allowed_ips").first()
            except Exception:
                config = None

            if config and config.ip_whitelist_enabled:
                ip = get_client_ip(request)
                entries = [e.ip_or_cidr for e in config.allowed_ips.all()]
                if not ip_in_list(ip, entries):
                    logger.warning("Blocked admin access attempt from %s", ip)
                    return JsonResponse({"detail": "Access denied."}, status=403)

        return self.get_response(request)
