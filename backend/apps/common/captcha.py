"""
Anti-bot verification: Cloudflare Turnstile primary, Google reCAPTCHA
fallback. When no secret keys are configured (e.g. local development
without third-party accounts), verification is skipped so the app remains
usable out of the box.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps.security")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_captcha(token: str, remote_ip: str = None, provider: str = "turnstile") -> bool:
    if not settings.CAPTCHA_ENFORCED:
        return True

    if not token:
        return False

    if provider == "recaptcha" and settings.RECAPTCHA_SECRET_KEY:
        return _post(RECAPTCHA_VERIFY_URL, settings.RECAPTCHA_SECRET_KEY, token, remote_ip)

    if settings.TURNSTILE_SECRET_KEY:
        if _post(TURNSTILE_VERIFY_URL, settings.TURNSTILE_SECRET_KEY, token, remote_ip):
            return True

    # Fall back to reCAPTCHA if Turnstile is unavailable/misconfigured.
    if settings.RECAPTCHA_SECRET_KEY:
        return _post(RECAPTCHA_VERIFY_URL, settings.RECAPTCHA_SECRET_KEY, token, remote_ip)

    return False


def _post(url: str, secret: str, token: str, remote_ip: str) -> bool:
    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        resp = requests.post(url, data=payload, timeout=3)
        resp.raise_for_status()
        return bool(resp.json().get("success"))
    except requests.RequestException as exc:
        logger.warning("Captcha verification request failed: %s", exc)
        return False
