# BaseWeb

A production-grade Django + DRF + React starter with JWT auth, email
verification, audit logging, geo/IP restrictions, and hardened defaults.

## Architecture

- **Backend**: Django 5 + Django REST Framework, JWT auth (SimpleJWT), a
  custom email-based User model, `apps/accounts`, `apps/audit`,
  `apps/security`.
- **Frontend**: React 18 + React Router 7 + Axios (Vite).
- **Database**: SQLite in development, PostgreSQL in production.
- **Reverse proxy**: NGINX, serving the built frontend and proxying
  `/api/` and the admin panel to the backend.
- **Deployment**: Docker Compose (`db`, `backend`, `nginx` services).

## Local development (no Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ENVIRONMENT=development
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

Visit `http://localhost:5173`. In development, verification/reset emails
are printed to the backend console (`EMAIL_BACKEND=console`), and
Turnstile/reCAPTCHA are skipped automatically when no secret key is
configured.

## Running tests

```bash
cd backend
source .venv/bin/activate
export ENVIRONMENT=development
python manage.py test apps
```

## Docker / production

```bash
cp .env.example .env   # fill in real secrets
docker compose build
docker compose up -d
```

This builds three images: `db` (Postgres), `backend` (Gunicorn, runs
migrations + `collectstatic` on start via `entrypoint.sh`), and `nginx`
(multi-stage: builds the React app, then serves it + proxies `/api/` and
`ADMIN_URL` to the backend). Static/media files are shared with nginx via
Docker volumes.

Note: `VITE_*` variables are baked into the frontend bundle at **build**
time (they're passed as Docker build args), not read at container
runtime — rebuild the `nginx` image if you change them.

## Security implementation notes

- **Custom User model** (`apps/accounts/models.py`): email as username,
  required profile fields, `is_active=False` until email verification.
- **Encryption at rest**: phone numbers are encrypted with Fernet, keyed
  by `ENCRYPTION_KEY` (`apps/common/encryption.py` — a small
  self-contained field equivalent to `django-fernet-fields`, so behavior
  isn't dependent on a third-party package's exact API).
- **JWT auth**: unverified users can still obtain tokens (needed so they
  can view their profile / resend verification / log out), enforced via
  a custom `USER_AUTHENTICATION_RULE` and a custom `JWTAuthentication`
  subclass; every other endpoint requires `IsVerified`.
- **MFA readiness**: `apps.accounts.models.MFAMethod` models email-OTP and
  TOTP methods per user without wiring them into the login flow yet.
- **Rate limiting**: `django-axes` for login lockout (5 failures / 15 min
  cooldown), DRF `ScopedRateThrottle` for register/login/password-reset/
  resend-verification.
- **Anti-bot**: Cloudflare Turnstile primary, Google reCAPTCHA fallback
  (`apps/common/captcha.py`); skipped automatically when no secret key is
  configured (e.g. local dev).
- **Geo/IP restrictions**: `apps/security` middleware, configurable via
  Django admin (whitelist/blacklist for both), enforced before
  authentication; every block is written to `AuditLog`.
- **Trusted proxies**: `X-Forwarded-For` is only honored when
  `REMOTE_ADDR` matches an entry (IP or CIDR) in `TRUSTED_PROXY_IPS`.
- **Audit logging**: `LoginAudit` (login/logout/failed attempts) plus a
  general `AuditLog` covering registration attempts, password/email/role
  changes, account activation, geo/IP blocks, and admin actions (hooked
  into `django.contrib.admin`'s `LogEntry`).
- **Admin hardening**: served at `ADMIN_URL` (never `/admin/`), optional
  IP whitelist via `AdminSecuritySettings`, short session lifetime.
- **Fail-secure config**: `config/env.py` raises `ImproperlyConfigured`
  at startup if a required production variable is missing.

## Known trade-offs

- `npm audit` reports one dev-only moderate advisory in `esbuild`
  (Vite 5's bundled dev-server dependency); fixing it requires the
  Vite 8 major upgrade. It only affects `npm run dev`, not the
  production build/bundle.
- GeoIP resolution defaults to the free `ip-api.com` lookup with no API
  key; set `GEOIP_PROVIDER=ipinfo` + `GEOIP_API_KEY` for a paid provider.
