# Production security hardening

The authoritative Mac mini deployment is the existing infrastructure Helm chart
at `public/iam/templates/api.yaml`: one Genesis replica, `Recreate` updates, one
API worker, existing MySQL, and keys mounted from a Kubernetes Secret. Public
traffic already passes through Cloudflare and Traefik. **No Redis or other new
service is needed.** The limiter uses the same implementation in development and
production. The Helm chart supplies production mode, allowed public/internal
hosts, probe Host headers, and the bootstrap password through the existing
Secret workflow. The standalone Compose configuration below is a separate
deployment option.

## Rate limits

The API defaults to **30 requests in a rolling one-second window per IP**, across
all routes and methods. Login, admin login, registration, OAuth token requests,
and SSO flow endpoints also share **10 requests per minute per IP**. The native
refresh endpoint allows **60 requests per minute per IP**. Rejections return
HTTP 429 with `Retry-After`. Invalid requests consume the same limits as valid
ones. Request bodies are limited to 6 MiB, including chunked uploads, before
parsing; avatar files retain their 5 MiB allowance.

Thirty API requests per second is a starting point for ordinary browsing, not a
measured capacity guarantee. Users behind a shared office/mobile/VPN address
share a budget; monitor 429s and adjust for real traffic. A crawler can stay
below the limit or rotate IPs. Use an ingress/CDN/WAF for bot management and
distributed abuse, connection limits, and request/body timeouts. Do not rely on
User-Agent strings or robots.txt to enforce access controls.

The frontend nginx independently limits page/assets traffic to 30 requests per
second with a burst allowance of 60 to accommodate initial asset loads. This
is an average-rate/burst policy, whereas the API uses a strict rolling window.

API limits and expiring, single-use SSO state live in bounded, thread-safe
process memory. The entrypoint explicitly starts one worker, matching the
existing Helm deployment. Each of the rate/state maps holds at most 10,000 keys;
if full, a new key fails closed with HTTP 503 until capacity is available. Rate
expiry uses one scheduled entry per tracked key and does not scan the entire
IP map on each request. No network call or database write is needed per check.

Process restarts clear counters and pending SSO flows, which must restart
authorization. Existing MySQL sessions and revocations remain persistent. If
the deployment later adds workers or replicas, each would have an independent
budget and SSO store; reassess shared coordination then. Options include the
existing ingress for rate limiting and existing MySQL for single-use state.
Redis is one possible alternative at that point, not a prerequisite for this
deployment. See [the measured decision](redis-decision.md) for the comparison.

## Required production configuration

The production Compose file now requires explicit secrets and HTTPS settings.
Create a private environment file with values appropriate for your deployment:

```dotenv
DB_ROOT_PASSWORD=<independent-random-database-root-password>
DB_PASSWORD=<independent-random-database-application-password>
BOOTSTRAP_ROOT_PASSWORD=<strong-bootstrap-password>
OAUTH_ISSUER=https://auth.example.com
CORS_ORIGINS=https://app.example.com
ALLOWED_HOSTS=auth.example.com
RATE_LIMIT_PER_SECOND=30
AUTH_RATE_LIMIT_PER_MINUTE=10
REFRESH_RATE_LIMIT_PER_MINUTE=60
```

The bootstrap password must meet the password policy (12-128 characters, upper
and lower case, a number and one of `@#$%^&+=!`). It is used only when creating the first
ROOT user, and production never prints it. Supplying a different value later
does not reset an existing ROOT password. Protect the environment file and use
your deployment secret manager where available.

Standalone Compose sets `ENVIRONMENT=production`.
To opt into this stricter configuration mode in other deployment systems, set
these explicitly along with
`CORS_ALLOW_ORIGINS`, the database settings, and the RSA key paths. Production
rejects wildcard hosts/origins, non-HTTPS origins, or missing RSA key paths.
Startup verifies that a matching RSA key pair (at least 2048 bits) is available.
Production mode cannot fall back to the development HMAC secret. The Mac mini
Helm chart now enables these checks for both public dev and prod environments.
Run `make secrets` in the infrastructure repository before upgrading Genesis:
it adds `GENESIS_BOOTSTRAP_ROOT_PASSWORD` to old secret files and the existing
`genesis-db` Secret without changing database or existing ROOT passwords. New
databases use that bootstrap value. `make genesis-root-password` saves the
initial ROOT credential privately; production no longer prints it.

The `signing_keys` volume preserves signing keys across container recreation.
For multiple replicas, provision the same pair before starting them; keep
backups and restrict access to the private key. Keep the uploads volume as well.
Secrets, uploads, and local environment files are excluded from the API build
context. The production API host port binds to loopback by default.

The frontend API URL is compiled into its JavaScript. Build its production image
with the HTTPS API origin, then use that image in your deployment:

```sh
docker build --build-arg VUE_APP_API_URL=https://auth.example.com \
  -t your-registry/genesis-web:production ./web
```

The default web build still targets localhost for development. Setting a
container environment variable after the web image was built does not change
the compiled URL. Build/release both changed images before deploying this code.

## Trusted proxies and TLS

Terminate TLS at your ingress/reverse proxy. Forward the original Host and
scheme and overwrite the incoming client-IP header. Set `FORWARDED_ALLOW_IPS`
to the exact addresses/CIDRs of proxies that can directly reach Uvicorn; the
default trusts only `127.0.0.1`. Never set it to `*` on an exposed service.
If a host proxy reaches Docker through a bridge gateway, configure that actual
peer address. The limiter uses the transport IP after Uvicorn's trusted-proxy
processing and never directly trusts `X-Forwarded-For` or `X-Real-IP`.

When frontend nginx is behind another proxy, configure nginx's real-IP module
with only that proxy's addresses and an overwritten forwarding header. Otherwise
all visitors can share the proxy's rate budget. Verify real-client attribution
from two clients through the actual ingress before rollout. Keep the API port
private to prevent bypassing ingress protection. Apply TLS/HSTS at the ingress
for the frontend; HTTPS API responses include HSTS automatically when the
forwarded scheme is trusted.

## Access, validation, and concurrency fixes

- Registration remains public. User listing/search require admin/root access;
  individual account reads/updates/deletes require the owner or an admin/root.
  ROOT cannot be deleted; other administrators cannot change its password or
  demote it. Existing integrations using anonymous user CRUD must authenticate.
- Revoked/expired user sessions invalidate access-token use on the user API,
  profile API, UserInfo, and token validation, as well as refresh. Refresh tokens
  require an owned session; old sessionless tokens require a new login.
  Password changes revoke existing sessions and require signing in again.
  Changing an email address clears its verification status.
- Refresh rotation uses a conditional database update. Authorization-code
  redemption atomically consumes the unused, unexpired code. Existing replay
  detection still revokes the affected session, including simultaneous refresh
  attempts; clients should coordinate refreshes to avoid racing themselves.
- Session creation serializes per user and uses current locking reads even
  when authentication already opened a MySQL repeatable-read snapshot.
- Migration **004** enforces one profile per user and one link per SSO provider
  per user. It refuses existing duplicates without deleting data. Inspect and
  resolve duplicate `(profiles.user_id)` or `(oauth_accounts.user_id, provider)`
  values before upgrading. Back up the database and run `alembic upgrade head`
  before starting the new application (the container entrypoint does this).
  Stop application writes while applying this MySQL DDL migration.
- Duplicate registration/update/link writes return a client error after rollback.
  Provider unlinking serializes checks to preserve the last authentication method.
- SSO auto-linking requires the provider to verify the incoming email **and** the
  local account's email to be verified in Genesis (2026-10 change; see below). GitHub verification comes from its email API.
  Callback state is browser-bound with an HttpOnly, SameSite=Lax cookie, expires
  after ten minutes, and can be consumed once. A cross-browser or cookie-less
  callback must restart authorization.
- Password byte limits, database string lengths, unsafe redirect/picture URLs,
  malformed Basic credentials, and invalid PKCE parameters are validated.
  Invalid/corrupt images and excessive pixel dimensions return client errors;
  storage keys cannot escape the upload directory. Avatar replacement commits
  before deleting the old file, and concurrent avatar changes lock the profile.
- API responses disable caching and include frame, MIME, and referrer protection.
  The JWT implementation uses PyJWT with explicit algorithms and required claims,
  replacing the dependencies flagged by the security scan. JWT claims, RSA
  signatures, and existing successful auth flows remain interoperable.

## Verification and remaining limits

Run isolated tests without a server:

```sh
python -m pytest tests/security -q
```

To include the MySQL integration cases, point this variable at a disposable
test database. Its name must end in `_security`; **these integration
tests drop and recreate that database's application tables**:

```sh
GENESIS_TEST_DATABASE_URL=mysql+pymysql://test:password@127.0.0.1/genesis_security \
python -m pytest tests/security -q
```

The PR workflow runs these integration tests using disposable service containers.
When Helm and the adjacent infrastructure checkout are available, deployment
contract tests also render both environment configurations and check production
startup, host restrictions, health probes, JWKS, and CORS. Set
`GENESIS_INFRA_ROOT` to select a different checkout.
The security tests include atomic in-process limits and SSO state, real MySQL 8
races, and the existing end-to-end suite. The Redis removal and performance
verification are recorded in [the measured decision](redis-decision.md).
Migration 004 upgrade, downgrade, and re-upgrade, nginx configuration, and the
HTTPS standalone frontend build were also checked in the initial sweep.
The legacy end-to-end suite runs separately with higher test-only rate limits,
because it sends many credential requests from one IP; dedicated security tests
exercise the actual default limits. The older standalone test scripts outside
`tests/security` require a running server and some assume the formerly public
user-management endpoints; they are not the isolated security suite.

The resolved Python requirements and frontend production dependencies passed
their vulnerability audits on 2026-10-16. The legacy Vue CLI build stage still
reported 42 dependency advisories (23 moderate, 19 high); these packages are not
copied into the final nginx image. Migrating that build toolchain needs a separate
compatibility review. Repeat dependency and container-image scans for the exact
artifacts you release; this sweep does not certify infrastructure, live SSO
provider configuration, or resilience under production load.

References: [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
[nginx request limiting](https://nginx.org/en/docs/http/ngx_http_limit_req_module.html),
[GitHub email verification](https://docs.github.com/en/rest/users/emails),
[PyJWT validation](https://pyjwt.readthedocs.io/en/latest/usage.html).

## 2026-10 auth hardening

Summary of the changes from the authentication audit (full report:
[`docs/audits/auth-audit-2026-10-19.md`](audits/auth-audit-2026-10-19.md); libraries: [`backend.md`](../backend.md),
[`frontend.md`](../frontend.md)).

- Passwords: Argon2id via pwdlib (m=19 MiB, t=2, p=1, at most 4 hashes at once); bcrypt hashes upgrade on login.
  Passwords may be 12-128 characters (the 72-byte bcrypt limit is gone).
- Per-account lockout after 5 failures in 15 minutes (429, doubling up to 15 minutes), including unknown usernames.
- `PUT /users/{id}` no longer changes passwords. Use `POST /users/me/password` (current password required; SSO-only
  accounts need a sign-in from the last 10 minutes) or `POST /admin/users/{id}/password`. Changing your own email
  needs `current_password`.
- Only ROOT manages admin accounts (role changes, disable, delete, password reset). Role changes and disabling
  revoke the target's sessions; the `role` claim is in every user token and can be stale for up to the access-token
  lifetime in relying parties that validate offline.
- OIDC: refresh tokens are bound to their client; non-first-party clients need consent; `/oauth/token` client
  secrets are SHA-256 (legacy bcrypt upgraded on use) and checked off the event loop.
- SSO: Authlib client with PKCE and nonce, Google ID-token verification, no stored provider tokens, browser-bound
  hand-off to the web app.
- No committed HS256 secret; missing key files stop startup in every environment.
- Optional email verification (`EMAIL_VERIFY`, default false). Enabling it on an existing database requires existing
  unverified users to verify (via `POST /auth/email/resend`) before password sign-in.
- Emergency password reset: `python -m app.cli reset-password USERNAME` (password from stdin, never printed).
