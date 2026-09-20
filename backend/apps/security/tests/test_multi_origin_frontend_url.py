"""
Regression test for a real production incident: FRONTEND_URL set to a
comma-separated list of origins (e.g. an http and https variant during a
TLS transition) crashed the app on startup with corsheaders.E014, because
production settings wrapped the raw FRONTEND_URL string in a single-item
list instead of parsing it as a list of origins.

This spawns a real `manage.py check` subprocess with ENVIRONMENT=production
and a comma-separated FRONTEND_URL, exactly reproducing the failure as it
actually happened, rather than only unit-testing the parsing logic.
"""
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BACKEND_DIR = Path(__file__).resolve().parents[3]


def run_check(frontend_url):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "ENVIRONMENT": "production",
        "SECRET_KEY": "test-secret-key-for-check-only",
        "ENCRYPTION_KEY": "n-argOQziUkccLYxpR0P_uqV8pav8kQae9C_xDtyQhI=",
        "ALLOWED_HOSTS": "example.com",
        "DATABASE_ENGINE": "django.db.backends.sqlite3",
        "DATABASE_NAME": "/tmp/regression_check.sqlite3",
        "DATABASE_USER": "x",
        "DATABASE_PASSWORD": "x",
        "DATABASE_HOST": "x",
        "DATABASE_PORT": "5432",
        "EMAIL_HOST": "x",
        "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": "x",
        "EMAIL_HOST_PASSWORD": "x",
        "DEFAULT_FROM_EMAIL": "x@example.com",
        "STATIC_ROOT": "/tmp/regression_static",
        "MEDIA_ROOT": "/tmp/regression_media",
        "EXPORTS_ROOT": "/tmp/regression_exports",
        "FRONTEND_URL": frontend_url,
    }
    return subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


class MultiOriginFrontendUrlTests(SimpleTestCase):
    databases = []

    def test_comma_separated_frontend_url_does_not_crash_production_check(self):
        result = run_check("http://battleground.yuziva.com,https://battleground.yuziva.com")
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, combined)
        self.assertNotIn("corsheaders.E014", combined)
        self.assertNotIn("SystemCheckError", combined)

    def test_single_frontend_url_still_works(self):
        result = run_check("https://example.com")
        combined = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, combined)
        self.assertNotIn("SystemCheckError", combined)
