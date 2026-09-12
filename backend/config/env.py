"""
Central environment-variable access with fail-secure behaviour.

Every configuration value used by the application MUST be read through this
module. When ENVIRONMENT=production, any required variable that is missing
raises ImproperlyConfigured at import time, so the process refuses to start
instead of silently falling back to an insecure default.
"""
import sys
from django.core.exceptions import ImproperlyConfigured
from decouple import config as _decouple_config, Csv

ENVIRONMENT = _decouple_config("ENVIRONMENT", default="development")
IS_PRODUCTION = ENVIRONMENT == "production"

_MISSING = object()


def env(key, default=_MISSING, cast=None, required_in_production=False):
    """
    Fetch an environment variable.

    - If `required_in_production` is True and ENVIRONMENT=production and the
      variable is unset, the application fails to start.
    - Otherwise falls back to `default` (or None if not provided).
    """
    kwargs = {}
    if cast is not None:
        kwargs["cast"] = cast

    if required_in_production and IS_PRODUCTION:
        try:
            return _decouple_config(key, **kwargs)
        except Exception as exc:
            raise ImproperlyConfigured(
                f"Required production environment variable '{key}' is missing. "
                "Refusing to start with an insecure/incomplete configuration."
            ) from exc

    if default is _MISSING:
        return _decouple_config(key, default=None, **kwargs)
    return _decouple_config(key, default=default, **kwargs)


def env_list(key, default="", required_in_production=False):
    return env(key, default=default, cast=Csv(), required_in_production=required_in_production)


def env_bool(key, default=False, required_in_production=False):
    return env(key, default=default, cast=bool, required_in_production=required_in_production)


def fail(message):
    """Abort process startup with a clear security-relevant error message."""
    raise ImproperlyConfigured(message)
