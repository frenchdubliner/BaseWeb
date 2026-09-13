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

### Creating a superuser inside Docker

```bash
docker compose exec backend python manage.py createsuperuser
```

It prompts interactively for each required field:

- **Email** is the username field - there's no separate username prompt.
- **Dropoff location** / **payment preference** expect the *stored* value,
  not the display label - type exactly `abington`, `norton`, `saugus`, or
  `framingham`, and `store_credit_70` or `cash_40`.
- **Phone number** needs international format, e.g. `+14155552671`.

Superusers are created with `is_active=True` immediately (no email
verification needed). Log into the admin panel at
`http://<your-host>/<ADMIN_URL>/` with that email/password.

If `docker compose exec` hangs or exits with no output at all, that's a
known issue with some Docker installs (e.g. the Canonical snap package's
confinement) rather than anything wrong with the app — see "Deploying to
a production server" below for a plain `docker` (non-snap) install, which
doesn't have this problem.

### Deploying to a production server

This assumes a fresh Linux server (Ubuntu/Debian) with a domain name's
DNS **A record** already pointed at its public IP, and ports 80/443 open
in whatever firewall/security group sits in front of it.

1. **Install Docker** on the server. Prefer the official `apt` packages
   over the Docker snap — some snap installs have a broken/confined
   `docker exec` (harmless for `up`/`build`, but you'll want `exec` to
   work for `createsuperuser`, one-off management commands, etc.):

   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER   # log out/in (or `newgrp docker`) after this
   ```

2. **Copy the project to the server.** Don't copy your local `.env` or
   `backend/.env` — those hold dev/test secrets. Either `git clone` the
   repo on the server, or `rsync`/`scp` it over excluding env files:

   ```bash
   rsync -avz --exclude='.env' --exclude='backend/.env' --exclude='node_modules' \
       --exclude='.venv' --exclude='__pycache__' \
       ./ user@your-server:/opt/baseweb/
   ```

3. **Create a real `.env` on the server** (`cp .env.example .env`, then
   fill it in) with:
   - A freshly generated `SECRET_KEY` and `ENCRYPTION_KEY` (don't reuse
     the ones from any other environment):
     ```bash
     cd backend && source .venv/bin/activate  # or run this step locally before copying nothing but the values over
     python3 -c "from django.core.management.utils import get_random_secret_key; from cryptography.fernet import Fernet; print(get_random_secret_key()); print(Fernet.generate_key().decode())"
     ```
   - `ALLOWED_HOSTS`, `FRONTEND_URL`, and `VITE_API_URL` set to your real
     domain (e.g. `https://example.com`) — **not** `localhost`.
   - Real `DATABASE_PASSWORD`, `EMAIL_*`, and Turnstile/reCAPTCHA keys.
   - `SECURE_SSL_REDIRECT=True` (the default) once you've completed the
     SSL section below — leave it `False` only until the certificate
     exists, otherwise every request 301-redirects to an HTTPS port
     nothing is listening on yet.

4. **Build and start it:**

   ```bash
   docker compose build
   docker compose up -d
   ```

5. **Create your admin account** (see above), then get a certificate
   (next section) before advertising the site publicly.

### Free SSL certificate (Let's Encrypt)

The stack ships with everything needed to obtain and use a free
[Let's Encrypt](https://letsencrypt.org) certificate via `certbot`, using
the HTTP-01 "webroot" method — nginx already has a
`/.well-known/acme-challenge/` location wired up for it, and
`docker-compose.yml` has an opt-in `certbot` service (it only runs when
you explicitly `docker compose run` it, never on a plain `up`).

This requires a real domain pointed at the server (Let's Encrypt won't
issue a certificate for `localhost` or a bare IP address).

1. Make sure the stack is already up and reachable on port 80 at your
   domain (the challenge is served over plain HTTP first):

   ```bash
   docker compose up -d
   ```

2. Request the certificate (replace both the domain and the email):

   ```bash
   docker compose run --rm certbot certonly \
     --webroot -w /var/www/certbot \
     -d your-domain.com \
     --email you@example.com --agree-tos --no-eff-email
   ```

   This saves the certificate into the `certbot_conf` Docker volume,
   already mounted read-only into the `nginx` container at
   `/etc/letsencrypt`.

3. Edit `nginx/nginx.conf` to redirect HTTP to HTTPS and serve the app on
   443, replacing its single `server {}` block with:

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location /.well-known/acme-challenge/ {
           root /var/www/certbot;
       }

       location / {
           return 301 https://$host$request_uri;
       }
   }

   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

       client_max_body_size 10M;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-Frame-Options "DENY" always;
       add_header Referrer-Policy "same-origin" always;

       location /static/ {
           alias /app/staticfiles/;
           access_log off;
           expires 30d;
       }

       location /media/ {
           alias /app/media/;
           access_log off;
       }

       location /api/ {
           proxy_pass http://backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /${ADMIN_URL} {
           proxy_pass http://backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location / {
           root /usr/share/nginx/html;
           try_files $uri $uri/ /index.html;
       }
   }
   ```

4. Rebuild nginx (the config file is baked into its image at build time)
   and set `SECURE_SSL_REDIRECT=True` + `FRONTEND_URL`/`VITE_API_URL` to
   `https://your-domain.com` in `.env`, then bring everything back up:

   ```bash
   docker compose build nginx backend
   docker compose up -d
   ```

5. **Set up auto-renewal.** Certificates expire after 90 days. Add a host
   crontab entry that renews and reloads nginx:

   ```bash
   # crontab -e
   0 3 * * * cd /opt/baseweb && docker compose run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
   ```

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

## Two separate `.env` files - don't mix them up

- **`backend/.env`** - local (non-Docker) development. `python-manage.py`
  runs from `backend/` read this one.
- **`.env`** (repo root) - used only by `docker compose` (`env_file: .env`
  in `docker-compose.yml`).

They're deliberately kept apart: `python-decouple` searches upward through
parent directories for a `.env` file, so without a `backend/.env` present,
local runs would silently fall through to the repo-root one and pick up
Docker/production secrets (real Turnstile keys, `SECRET_KEY`, etc.) by
accident. Don't delete `backend/.env`, even if empty.

## Known trade-offs

- `npm audit` reports one dev-only moderate advisory in `esbuild`
  (Vite 5's bundled dev-server dependency); fixing it requires the
  Vite 8 major upgrade. It only affects `npm run dev`, not the
  production build/bundle.
- GeoIP resolution defaults to the free `ip-api.com` lookup with no API
  key; set `GEOIP_PROVIDER=ipinfo` + `GEOIP_API_KEY` for a paid provider.
