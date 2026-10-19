# Genesis backend: libraries and why we use them

Genesis is an identity provider written in Python. This page lists every library the API depends on, what it does for us, and why we picked it. Versions are the ones pinned in [`requirements.lock`](requirements.lock) (runtime) and [`requirements-dev.lock`](requirements-dev.lock) (tests). Those were resolved on 2026-10-19 for Python 3.13.

**How dependencies are managed:**
- [`requirements.txt`](requirements.txt) lists our direct dependencies with version ranges.
- The lockfiles pin every package exactly, including indirect ones. Regenerate them with:
  ```bash
  uv pip compile --universal --python-version 3.13 requirements.txt -o requirements.lock
  ```
  (and the same for `requirements-dev.txt` → `requirements-dev.lock`).
- The Docker image installs from `requirements.lock`, so every build gets the same versions.

---

## How authentication fits together

```
Browser / SPA / OAuth clients
      │  HTTPS
      ▼
FastAPI app (one uvicorn worker)
  ├─ SecurityMiddleware: per-IP limits, body size limits, security headers
  ├─ Password sign-in ── pwdlib (Argon2id; old bcrypt hashes still accepted) + per-account lockout
  ├─ Tokens ─────────── PyJWT (RS256 in production) + a database session row per sign-in
  ├─ Google/GitHub/Facebook sign-in ── Authlib OAuth client (PKCE, nonce) + PyJWT for Google ID tokens
  ├─ Genesis as an OIDC server ── our own code: auth code + PKCE, refresh, client credentials, consent
  └─ Optional email verification ── standard-library smtplib
      │
      ▼
MySQL (SQLAlchemy + Alembic)
```

---

## Libraries

### Web framework and server

| Library | Version | What it does for Genesis | Why we use it / benefit |
|---|---|---|---|
| **FastAPI** | 0.147.0 | Routes, request validation, dependency injection (`Depends`) for authentication and authorization, OpenAPI docs | Authentication becomes a reusable dependency (`oauth_authenticate_current_user`, `require_admin`). Request bodies are validated by Pydantic before our code runs. Ordinary `def` endpoints run in a thread pool, which is where password hashing must happen; see the "async" note below. |
| **Starlette** | 1.9.0 | The engine under FastAPI: middleware, cookies, redirects, static files, TestClient | Our `SecurityMiddleware` is a plain ASGI middleware, so it can enforce rate and size limits before a request is even parsed. |
| **Uvicorn** (`[standard]`) | 0.54.0 | Runs the app (ASGI server). The standard extras add uvloop, httptools and websockets | It's fast and production-ready. `--forwarded-allow-ips` controls which proxies may set the client IP, which is what per-IP rate limiting relies on. |
| **python-multipart** | 0.0.32 | Parses form and multipart bodies | `/token` uses the OAuth2 form format, and avatars are uploaded as multipart. |

### Data and configuration

| Library | Version | What it does | Why / benefit |
|---|---|---|---|
| **Pydantic** (`[email]`) | 2.14.1 | Request and response models, validation (password policy, redirect-URI rules, email syntax) | Bad input is rejected at the edge. `SecretStr` keeps passwords and secrets out of logs and reprs. Clients can't set fields the models don't declare, such as role, owner, profile `sub` and `picture`. |
| **email-validator** | 2.3.0 | Email syntax checks behind `EmailStr` | Blocks malformed addresses and header-injection attempts. |
| **pydantic-settings** | 2.16.0 | Typed settings from environment variables and `.env` | Settings are validated at startup. Production refuses unsafe values: an HTTP issuer, wildcard hosts or CORS, missing RSA keys, a console mail backend, unencrypted SMTP. |
| **SQLAlchemy** | 2.1.5 | ORM and queries | Queries are parameterised, so no SQL injection. Row locks (`with_for_update`) and atomic `UPDATE … WHERE` make single-use codes, refresh rotation and the session cap safe when requests race. |
| **PyMySQL** | 1.2.3 | Pure-Python MySQL driver | No compiled client library needed, so the image stays small and simple. |
| **Alembic** | 1.20.0 | Schema migrations (`alembic/versions/001`–`005`) | Migrations run automatically on container start (`entrypoint.sh`) and can be rolled back. |

### Security libraries

| Library | Version | What it does | Why / benefit |
|---|---|---|---|
| **pwdlib** (`[argon2,bcrypt]`) | 0.3.1 | Password hashing: `PasswordHash((Argon2Hasher, BcryptHasher))`, `hash`, `verify_and_update` | A small, modern wrapper that FastAPI's docs recommend. New hashes are **Argon2id**. Hashes from before the switch are **bcrypt** and keep working, and `verify_and_update` replaces them with Argon2id at the next successful login, with no bulk migration and no lockouts. Each hash gets a fresh random salt, stored inside the hash string. pwdlib does **not** handle sessions, JWTs, authorization or peppers; that's our own code. |
| **argon2-cffi** | 25.1.0 | The Argon2 implementation pwdlib uses | A maintained binding to the reference Argon2 code. Argon2id is OWASP's first choice for password storage because it uses a lot of memory per guess, which makes GPU cracking expensive. |
| **bcrypt** | 5.0.0 | Checks legacy hashes, and can still write them if `PASSWORD_HASH_SCHEME=bcrypt` | Needed until every old hash has been upgraded. Note that bcrypt only reads the first 72 bytes of a password and version 5 rejects anything longer; our verify wrapper treats that as a wrong password instead of crashing. |
| **PyJWT** (`[crypto]`) | 2.15.1 | Signs and verifies our JWTs (RS256 in production). `PyJWKClient` verifies Google ID tokens against Google's published keys | One JWT library for everything. Verification always pins the algorithm and requires `exp`, `iat`, `nbf`, `iss`, `aud`, `sub` and `jti`, which blocks algorithm-swap attacks and wrong-audience tokens. *We no longer use python-jose;* it is less actively maintained. |
| **cryptography** | 50.0.2 | Loads RSA keys and checks they are a matching pair of at least 2048 bits; builds the JWKS document; backs PyJWT's RS256 | The standard, audited crypto library for Python. |
| **Authlib** | 1.9.1 | The OAuth 2.0 client for Google, GitHub and Facebook sign-in: authorization URLs, PKCE (S256), the token exchange, client authentication | It replaces hand-written protocol code with a maintained implementation, and added PKCE for Google and GitHub, so a stolen authorization code is useless without the verifier. The verifier and nonce stay on the server, and provider errors are logged rather than shown to the user. Genesis's **own** OIDC server is still our code. Authlib isn't needed to validate our own JWTs, and it doesn't do password hashing. |
| **httpx** | 0.28.1 | Async HTTP client (Authlib's transport) for provider token and userinfo calls | Async, so a slow provider doesn't tie up the worker, and it has timeouts. |
| **itsdangerous** | 2.2.0 (via `fastapi[all]`) | Not used by Genesis code | Comes in as part of FastAPI's "all" extras. |

### Files and utilities

| Library | Version | What it does | Why / benefit |
|---|---|---|---|
| **Pillow** | 13.0.0 | Decodes, checks, resizes and re-encodes avatar uploads to WebP | Re-encoding removes anything hidden in an uploaded file, and the size/pixel limits stop "decompression bomb" images. |
| **boto3** | 1.43.114 | Optional S3 storage for avatars (`STORAGE_BACKEND=s3`) | The standard AWS SDK. It's only imported when S3 is turned on. |
| **user-agents** | 2.2.0 | Turns a User-Agent string into a device name for the sessions list | Lets users recognise their own sessions before revoking them. |

### Standard library (no extra dependency)

| Module | Used for |
|---|---|
| `smtplib`, `email.message`, `ssl` | Sending verification emails (STARTTLS or TLS; certificate checks on by default). |
| `secrets`, `hashlib`, `hmac` | Random tokens and codes; SHA-256 hashes of verification tokens and client secrets; constant-time comparisons. |
| `threading` | The thread-safe in-memory rate/state store, and the semaphore that limits how many password hashes run at once. |

### Test-only (`requirements-dev.txt`)

| Library | Version | Use |
|---|---|---|
| **pytest** | 9.1.1 | `tests/security/` runs on SQLite with no running server. MySQL concurrency tests run when `GENESIS_TEST_DATABASE_URL` is set. |
| **requests**, **Faker** | 2.34.2, 40.43.0 | Older end-to-end scripts that call a running server. |

---

## Choices worth knowing

### Argon2id settings (benchmark, 2026-10-19)
Measured on Apple Silicon (macOS, Python 3.13), 20 runs each, with a separate process per setting:

| Setting | Hash p50 / p95 | 4 hashes at once (peak RSS) |
|---|---|---|
| bcrypt cost 12 (old default) | 286 / 290 ms | 15 MiB |
| **Argon2id m=19 MiB, t=2, p=1 (OWASP minimum, chosen)** | **26 / 27 ms** | **93 MiB** |
| Argon2id m=46 MiB, t=1, p=1 (OWASP) | 39 / 44 ms | 201 MiB |
| Argon2id m=64 MiB, t=3, p=4 (pwdlib default) | 43 / 54 ms | 273 MiB |

- **How the setting was chosen:** the strongest OWASP setting that still fits the minikube pod's 512 MiB memory limit with 4 hashes running at once (`PASSWORD_HASH_CONCURRENCY=4`, a 128 MiB budget).
- **Salts:** all 20 hashes of the same password were different, and every one verified.
- **Tuning:** change `PASSWORD_ARGON2_*` and benchmark again on the target hardware before raising memory. Raising `PASSWORD_ARGON2_TIME_COST` adds CPU time without adding memory.
- **Busy server:** if every hashing slot is taken for 10 seconds, the request gets 503 with `Retry-After` instead of running the pod out of memory.

### Pepper: deliberately not used (for now)
- **What a pepper would add:** protection when the database is stolen *without* the app's secrets.
- **Why that doesn't help us yet:** our secrets (environment variables and PEM files) sit next to the app, there's no separate secret store yet, and losing a pepper would lock out every password user.
- **When to revisit:** once there's a KMS or Vault-style store that is kept apart from database backups.
- **Never reuse a signing key:** a JWT signing key or `OAUTH_SECRET_KEY` must never double as a pepper.

### Why OAuth client secrets use SHA-256, not Argon2
- Client secrets are 256-bit random values, so they can't be guessed and a slow hash adds nothing.
- SHA-256 with a constant-time comparison is enough, and it keeps `/oauth/token` fast.
- Old bcrypt client hashes are upgraded to SHA-256 the first time they're used successfully.

### Async handlers and blocking work
- **The rule:** CPU-heavy work (password hashing) and blocking database calls must not run inside `async def` endpoints, because that would freeze the single worker for everyone.
- **What changed:** `/oauth/token` and the role check are now plain `def`, so they run in the thread pool. The SSO callbacks stay `async` because of the provider HTTP calls, but their database work runs through `run_in_threadpool`.

### Per-account throttling
- **The policy:** 5 failed attempts within 15 minutes lock that username. The lock lasts 1 minute, then 2, then 4, and so on, up to 15 minutes, and the response is 429 with `Retry-After`.
- **No account discovery:** usernames that don't exist are locked the same way, and unknown users still go through a full hash check, so neither the lockout nor the response time reveals which accounts exist.
- **Same in-memory store as the per-IP limits:** see `docs/redis-decision.md` for why this store is enough with one replica.

### Optional email verification
- **Off by default** (`EMAIL_VERIFY=false`): Genesis runs with no mail service at all.
- **When it's on:**
  - registration sends a single-use link that expires after 24 hours (only a SHA-256 of the token is stored);
  - password sign-in needs a verified address;
  - an email change only takes effect once the new address is confirmed.
- **Development:** `docker-compose.yml` includes **mailpit**, which catches all mail at http://localhost:8025.
- **SSO linking:** an SSO sign-in is only merged automatically into an existing account if *both* the provider and Genesis have verified the email.

### Rollback notes
- **Older images can't read Argon2id hashes.** Once users have logged in on this version, their hashes are Argon2id. To roll back safely: first deploy with `PASSWORD_HASH_SCHEME=bcrypt` (still reads both, writes bcrypt), or reset passwords afterwards with `python -m app.cli reset-password USERNAME`.
- **Client secrets upgraded to SHA-256 need rotating** before going back to an older image.
- **Migration 005 can be downgraded**, but the stored provider tokens it removed are gone for good. Nothing ever used them.

---

## What's outdated or worth watching
- **`fastapi[all]` installs more than we use.** It brings in Jinja2, itsdangerous and others. Switching to `fastapi[standard]` plus explicit extras would shrink the image.
- **`datetime.utcnow()`** is deprecated in Python 3.12+. It still works, but moving to timezone-aware datetimes is a cleanup to do later.
- **The rate limiter and SSO state live in process memory.** That's correct for one replica; review it before adding replicas or workers.
