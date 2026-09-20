# BaseWeb

A production-grade Django + DRF + React starter with JWT auth, email
verification, audit logging, geo/IP restrictions, and hardened defaults.

## Architecture

- **Backend**: Django 5 + Django REST Framework, JWT auth (SimpleJWT), a
  custom email-based User model, `apps/accounts`, `apps/audit`,
  `apps/security`, `apps/listings` (game-for-sale listings, CRUD scoped to
  the owning user).
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

### Backing up and restoring the database

**Docker / production (PostgreSQL)**

The `db` service already has `POSTGRES_USER`/`POSTGRES_DB` set in its own
environment (from `DATABASE_USER`/`DATABASE_NAME` in `.env`), so a dump
command run via `docker compose exec` can reference them directly without
retyping credentials:

```bash
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    > "backup-$(date +%Y%m%d-%H%M%S).sql"
```

This produces a plain-SQL dump (human-readable, portable across Postgres
versions) containing the full schema and all data - `.gitignore` already
excludes `.env` and the SQLite files, but a backup file like this should
never be committed either; keep it somewhere separate (off-server storage,
encrypted, etc.).

To restore it - **onto a freshly created, empty database** (e.g. setting
up a new server from a backup):

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backup-20260101-030000.sql
```

To restore **over an existing database that already has data in it**, the
tables from the dump would otherwise collide with the ones already there -
drop and recreate the schema first, then restore:

```bash
docker compose exec db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < backup-20260101-030000.sql
```

`DROP SCHEMA ... CASCADE` deletes every table and all their data first -
there is no undo. Only run it when the restore itself is the intent, and
take a fresh backup of the current state first if there's any doubt.

If the backup is older than the running code, apply any migrations that
were added since it was taken:

```bash
docker compose exec backend python manage.py migrate
```

Automate backups the same way as certificate renewal - a host crontab
entry, with a retention cleanup so old backups don't accumulate forever:

```bash
# crontab -e
0 2 * * * mkdir -p /opt/baseweb/backups && cd /opt/baseweb && docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > /opt/baseweb/backups/backup-$(date +\%Y\%m\%d).sql && find /opt/baseweb/backups -name '*.sql' -mtime +30 -delete
```

**Local development (SQLite)**

The dev database is a single file - back it up and restore it by copying
it (stop `manage.py runserver` first so nothing is mid-write):

```bash
cp backend/db.sqlite3 backend/db.sqlite3.bak   # backup
cp backend/db.sqlite3.bak backend/db.sqlite3   # restore
```

## Security implementation notes

- **CSP on the SPA itself** (`nginx/nginx.conf`, `location /`): the built
  React app's own `index.html`/JS/CSS are served directly by nginx and
  never pass through Django, so `django-csp`'s middleware never runs for
  them - discovered because the page that actually renders the
  Turnstile/reCAPTCHA widget had no `Content-Security-Policy` header at
  all. Nginx now sets the same policy directly on that location, scoped
  to it alone so proxied `/api/`/admin responses keep using Django's own
  header rather than getting a redundant second one. (Verified this
  wasn't the cause of a real "Captcha failed to load" report by A/B
  testing full registration attempts with the header present vs. removed
  - identical outcome either way, so it was safe to add and unrelated to
  that specific incident. See the "Anti-bot" note below for what
  actually explains that class of failure.)
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
  configured (e.g. local dev). **Turnstile site keys are domain-restricted
  in the Cloudflare dashboard** - if the widget shows "Captcha failed to
  load" on a real deployment despite the correct site key being baked
  into the build, check that the exact hostname (e.g.
  `battleground.yuziva.com`, plus `www.` if used) is added to that site
  key's allowed Domains list in Cloudflare. This is easy to miss because
  Cloudflare automatically allow-lists `localhost`/`127.0.0.1` for every
  site key, so local testing can never catch a missing production domain
  - the first real request from the actual domain is often the first
  time this gets exercised at all.
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
- **Game listings** (`apps/listings`): `/api/listings/` is a standard REST
  CRUD resource (`GameListingViewSet`), but its queryset is always
  filtered to `owner=request.user` - another user's listing doesn't 403,
  it simply doesn't exist as far as the endpoint is concerned (404),
  which avoids leaking whether a given listing ID belongs to someone
  else. Requires `IsVerified`, same as the rest of the authenticated app.
  Fields include an optional `missing_pieces_description` (shown in the UI
  only when "has missing pieces" is checked, and cleared server-side if
  that box is unchecked) and an optional `comments` field - both capped at
  64 characters. Frontend page: `/my-games`.
- **CSV bulk import** (`apps/listings/csv_import.py`): `GET
  /api/listings/csv-template/` downloads a heavily-commented example CSV
  (`#`-prefixed lines are documentation and are skipped by the importer);
  `POST /api/listings/bulk-upload/` (multipart, field name `file`, max 500
  rows, throttled at `listings-bulk-upload`: 20/hour) creates one listing
  per row for the uploading user. Best-effort, not all-or-nothing: valid
  rows are imported even if others fail, and every failure is reported
  with its row number and field errors. Accepts either the stored choice
  code (`very_good`) or its plain-English label (`Very Good`) for
  `condition`/`pet_exposure`, and tolerant boolean parsing
  (`TRUE`/`yes`/`1`/blank) for the checkbox columns.
- **Admin management UI** (`is_staff` only, gated by `AdminRoute` on the
  frontend and `IsAdminUser` on every endpoint below - a non-admin gets
  redirected client-side and 403s server-side either way):
  - `/admin/users` (`GET`/`PATCH /api/auth/admin/users/`): every user
    account, filterable by `email`, `first_name`, `last_name` (DB-level
    `icontains`) and `phone_number` (filtered in Python after decryption,
    since phone numbers are encrypted at rest and can't be queried at the
    DB level - see `apps/common/encryption.py`). Editing is limited to
    profile fields plus `is_active` (so an admin can manually verify a
    user); `is_staff`/`is_superuser` are read-only here by design - role
    changes stay in the Django admin panel, which has its own audit trail.
  - `/admin/games` (`GET`/`PATCH`/`DELETE /api/listings/admin/`): every
    listing from every user (not owner-scoped, unlike the regular
    endpoint), filterable by `id`, owner `email`/`first_name`/`last_name`,
    and `dropoff_location`. Supports edit and delete; `owner` itself is
    read-only (reassigning a listing to a different user is out of
    scope).
  - Both edits and deletes here write an `AuditLog` entry
    (`ADMIN_ACTION`) - edits made through the Django admin panel are
    already covered separately via the `LogEntry` signal, but these API
    routes bypass that panel entirely, so they log explicitly instead.
  - Implementation note: both admin route groups use `SimpleRouter`, not
    `DefaultRouter` - two `DefaultRouter`s sharing a `urls.py` each
    generate their own "API root" view bound to the empty path, and
    whichever is listed first silently shadows the other's list/create
    route. Hit this once during development; `SimpleRouter` sidesteps it
    by not generating that view at all.
- **Convention settings** (`apps/convention`): a single global convention
  name, `GET`/`PATCH /api/convention/`, admin-only. Same `SingletonModel`
  pattern as `apps/security`'s config models - there's always exactly one
  row, created on first access with the default name `PAXE2026` if no
  admin has changed it yet. Frontend page: `/admin/convention`.
- **Price tag PDF export** (`apps/listings/pdf.py`): `GET
  /api/listings/admin/<id>/print/` (admin-only) renders a single listing
  as a 2in x 3in price-tag PDF (convention name + game ID top right,
  game name, price, condition with its description, then every detail
  the seller entered) using `reportlab` - chosen over WeasyPrint/wkhtmltopdf
  specifically to avoid system-level Cairo/Pango dependencies in the
  Docker image. Long text is word-wrapped and, if it still doesn't fit,
  shrunk and then ellipsized rather than silently dropped or left to
  overflow the fixed page size - a single unbroken "word" wider than the
  tag (a real bug caught by rendering sample output during development,
  not just by tests) is now hard-clamped to width for the same reason.
  Frontend: a "Print" button per row on `/admin/games` downloads the file.
  `GET /api/listings/admin/print-all/` (same admin-only permission) takes
  the identical filter query params as the list endpoint and returns one
  PDF with one page per matching listing, via a shared `_draw_tag(canvas,
  listing, convention_name)` helper so the single- and multi-page paths
  can never drift apart from each other; capped at `MAX_PRINT_ALL` (500)
  listings per request. Frontend: "Print all filtered" next to the filter
  toggle on `/admin/games`, sending whatever filters are currently
  applied to the table (not whatever's typed but not yet applied).
- **`printed` lock** (`GameListing.printed`, default `False`): set to
  `True` automatically the first time either print action runs for a
  listing. Deliberately excluded from `GameListingSerializer` entirely
  (not just marked read-only) so it can never appear in - or be set
  through - anything the owner touches: their own create/list/retrieve/
  update responses, or CSV import (the column doesn't exist in the
  template and is silently ignored if present in an uploaded file,
  since `normalize_row()` only ever copies a fixed whitelist of known
  columns into the data it hands to the serializer). Once `True`, the
  owner's own `GameListingViewSet.perform_update`/`perform_destroy`
  raise `PermissionDenied` - with a message that itself never says
  "printed" ("This listing can no longer be edited/deleted."), since even
  an error string counts as exposing the attribute to its owner.
  `AdminGameListingSerializer` exposes the real `printed` field (read-only;
  only the print actions set it, not a direct edit) and
  `AdminGameListingViewSet` accepts it as a `?printed=true|false` filter.
  Admins can still edit/delete printed listings without restriction - the
  lock applies only to the owner-facing endpoint.

  The owner-facing `GameListingSerializer` does expose one derived,
  intentionally-named field: `can_edit` (`not printed`, computed in
  `get_can_edit()`) - a capability flag, not the underlying reason, so the
  frontend can hide the Edit/Delete buttons entirely once a listing is
  printed (`/my-games` shows a neutral "This listing can no longer be
  edited." note instead) without ever naming or exposing the `printed`
  attribute itself.

- **`received` toggle** (`GameListing.received`, default `False`):
  whether the physical game has actually arrived at the drop-off location.
  Same owner-invisibility as `printed` (excluded from
  `GameListingSerializer` entirely - never in a response, never settable,
  including via CSV), but unlike `printed` it's a direct, reversible admin
  action rather than something only the print actions set: `received` is
  a normal writable field on `AdminGameListingSerializer`, toggled via a
  plain `PATCH /api/listings/admin/<id>/` with `{"received": true|false}` -
  no dedicated endpoint needed. On `/admin/games`, a button to the left of
  Edit shows "Not Received" / "Received" reflecting the current state and
  flips it on click.

  Both this and the "Print" button update the on-screen list immediately
  from the API response (`setListings` merging the returned row into
  local state) rather than requiring a manual page reload - `handlePrint`
  and `handlePrintAll` previously downloaded the PDF but never updated
  local state, so the "Printed" column would silently stay stale until
  the next reload; fixed alongside adding `received` since both statuses
  have the same live-update requirement. `AdminGameListingViewSet` also
  accepts `?received=true|false` as a filter (combinable with `?printed=`
  and the rest), with a matching "Received" dropdown next to "Printed" in
  the `/admin/games` filter panel.

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
