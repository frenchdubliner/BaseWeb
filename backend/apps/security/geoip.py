"""
Pluggable GeoIP resolution. Disabled entirely unless GEOIP_ENABLED=True.

Supported GEOIP_PROVIDER values:
- "ip-api"  : https://ip-api.com (no key required, best-effort free tier)
- "ipinfo"  : https://ipinfo.io (requires GEOIP_API_KEY)

Results are cached for one hour per IP to avoid hammering the provider.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("apps.security")

CACHE_TTL = 60 * 60


def get_country_city(ip: str):
    """Returns (country_code, city) or (None, None) if unavailable/disabled."""
    if not settings.GEOIP_ENABLED or not ip:
        return None, None

    cache_key = f"geoip:{ip}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    result = (None, None)
    try:
        if settings.GEOIP_PROVIDER == "ipinfo":
            result = _lookup_ipinfo(ip)
        else:
            result = _lookup_ip_api(ip)
    except requests.RequestException as exc:
        logger.warning("GeoIP lookup failed for %s: %s", ip, exc)

    cache.set(cache_key, result, CACHE_TTL)
    return result


def _lookup_ip_api(ip: str):
    resp = requests.get(
        f"http://ip-api.com/json/{ip}",
        params={"fields": "status,countryCode,city"},
        timeout=2,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        return None, None
    return data.get("countryCode"), data.get("city")


def _lookup_ipinfo(ip: str):
    resp = requests.get(
        f"https://ipinfo.io/{ip}/json",
        params={"token": settings.GEOIP_API_KEY},
        timeout=2,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("country"), data.get("city")
