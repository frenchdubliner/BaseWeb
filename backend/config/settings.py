"""
Django settings for the BaseWeb project.

Behaviour branches on the ENVIRONMENT variable ("development" | "production").
See config/env.py for the fail-secure environment loading strategy.
"""
from datetime import timedelta
from pathlib import Path

from .env import ENVIRONMENT, IS_PRODUCTION, env, env_bool, env_list, fail

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-key", required_in_production=True)
DEBUG = not IS_PRODUCTION

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default="localhost,127.0.0.1", required_in_production=True)

ENCRYPTION_KEY = env("ENCRYPTION_KEY", default=None, required_in_production=True)
if not IS_PRODUCTION and not ENCRYPTION_KEY:
    # Deterministic dev-only key so migrations/tests work without a .env file.
    ENCRYPTION_KEY = "3JZ2h1S6y8b6b8b1S6y8b6b8b1S6y8b6b8b1S6y8b6c="

TRUSTED_PROXY_IPS = env_list("TRUSTED_PROXY_IPS", default="")

ADMIN_URL = env("ADMIN_URL", default="admin/")
if not ADMIN_URL.endswith("/"):
    ADMIN_URL = ADMIN_URL + "/"

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "axes",
    "csp",
    "phonenumber_field",
    # local
    "apps.accounts",
    "apps.audit",
    "apps.security",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Must run early: resolves the real client IP from trusted proxies only.
    "apps.security.middleware.TrustedProxyMiddleware",
    # IP restrictions are enforced before authentication.
    "apps.security.middleware.IPRestrictionMiddleware",
    "apps.security.middleware.GeoRestrictionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "apps.security.middleware.AdminAccessMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
if IS_PRODUCTION:
    DATABASES = {
        "default": {
            "ENGINE": env("DATABASE_ENGINE", default="django.db.backends.postgresql", required_in_production=True),
            "NAME": env("DATABASE_NAME", required_in_production=True),
            "USER": env("DATABASE_USER", required_in_production=True),
            "PASSWORD": env("DATABASE_PASSWORD", required_in_production=True),
            "HOST": env("DATABASE_HOST", required_in_production=True),
            "PORT": env("DATABASE_PORT", required_in_production=True),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.ComplexityPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "apps.accounts.backends.EmailBackend",
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media / exports
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

if IS_PRODUCTION:
    STATIC_ROOT = env("STATIC_ROOT", required_in_production=True)
    MEDIA_ROOT = env("MEDIA_ROOT", required_in_production=True)
    EXPORTS_ROOT = env("EXPORTS_ROOT", required_in_production=True)
else:
    STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
    MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
    EXPORTS_ROOT = env("EXPORTS_ROOT", default=str(BASE_DIR / "exports"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
if IS_PRODUCTION:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", required_in_production=True)
    EMAIL_PORT = env("EMAIL_PORT", cast=int, required_in_production=True)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", required_in_production=True)
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", required_in_production=True)
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", required_in_production=True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="localhost")
    EMAIL_PORT = env("EMAIL_PORT", default=25, cast=int)
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=False)
    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------
if IS_PRODUCTION:
    CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
    CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]
else:
    CORS_ALLOWED_ORIGINS = env_list(
        "CORS_ALLOWED_ORIGINS",
        default="http://localhost:5173,http://127.0.0.1:5173",
    )
    CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Session / cookie security
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # frontend must read it to set X-CSRFToken
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_AGE = 900  # 15 minutes, sliding
    SESSION_SAVE_EVERY_REQUEST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if TRUSTED_PROXY_IPS else None
else:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SESSION_COOKIE_AGE = 60 * 60 * 24

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# CSP (django-csp)
# ---------------------------------------------------------------------------
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'", FRONTEND_URL, "https://challenges.cloudflare.com", "https://www.google.com")
CSP_FRAME_SRC = ("https://challenges.cloudflare.com", "https://www.google.com")
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# ---------------------------------------------------------------------------
# django-axes (login rate limiting / lockout)
# ---------------------------------------------------------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True
AXES_ENABLE_ADMIN = True

# ---------------------------------------------------------------------------
# DRF / SimpleJWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.ActiveOrPendingJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "register": "10/hour",
        "login": "20/hour",
        "password-reset": "10/hour",
        "resend-verification": "10/hour",
    },
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_AUTHENTICATION_RULE": "apps.accounts.auth_rules.allow_inactive_user_authentication_rule",
}

# ---------------------------------------------------------------------------
# Anti-bot (Cloudflare Turnstile with Google reCAPTCHA fallback)
# ---------------------------------------------------------------------------
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
RECAPTCHA_SITE_KEY = env("RECAPTCHA_SITE_KEY", default="")
RECAPTCHA_SECRET_KEY = env("RECAPTCHA_SECRET_KEY", default="")
CAPTCHA_ENFORCED = bool(TURNSTILE_SECRET_KEY or RECAPTCHA_SECRET_KEY)

# ---------------------------------------------------------------------------
# GeoIP
# ---------------------------------------------------------------------------
GEOIP_ENABLED = env_bool("GEOIP_ENABLED", default=False)
GEOIP_PROVIDER = env("GEOIP_PROVIDER", default="ip-api")
GEOIP_API_KEY = env("GEOIP_API_KEY", default="")

# ---------------------------------------------------------------------------
# Encryption at rest (phone numbers, etc.)
# ---------------------------------------------------------------------------
# Consumed by apps.common.encryption

# ---------------------------------------------------------------------------
# Cache (used for geoip lookups + throttling)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps.security": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# Fail securely: refuse to boot in production with DEBUG on or a dev secret key.
if IS_PRODUCTION:
    if DEBUG:
        fail("DEBUG must be False in production.")
    if SECRET_KEY == "django-insecure-dev-only-key":
        fail("SECRET_KEY must be set to a strong, unique value in production.")
