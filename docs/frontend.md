# Genesis web app: libraries and why we use them

The Genesis web app ([`web/`](web/)) is a single-page Vue app. It covers sign-in, registration, profile, sessions, linking SSO accounts, email verification, the OAuth consent screen, and the admin console. This page lists what it's built with, why, and what each piece gives us. Versions come from [`web/package-lock.json`](web/package-lock.json), resolved on 2026-10-19.

**How dependencies are managed:**
- `package.json` lists version ranges; `package-lock.json` pins the exact tree.
- The Docker build runs `npm ci`, so every build installs exactly the locked versions.
- Update with `npm install`, then commit the lockfile.

---

## How the web app handles security

| Concern | How it's handled |
|---|---|
| **Where tokens live** | In memory only (Vuex state), never in `localStorage` or cookies readable by scripts. The trade-off: reloading the page signs you out. An HttpOnly refresh cookie is a planned follow-up. |
| **Token expiry** | Every API call goes through one helper (`authed()` in [`src/api.js`](web/src/api.js)). On a 401 it refreshes the session **once**, shared by any calls happening at the same time, and retries. If the refresh fails, it signs out and returns to the login page. |
| **Logout** | Calls `DELETE /auth/sessions/{sid}` before clearing state, so the server session and its refresh token stop working immediately. |
| **SSO sign-in** | The API redirects to `/sso/callback#code=…`. The code sits in the URL **fragment**, which browsers never send to servers or write to logs. The app removes it from the address bar and history straight away, then swaps it for tokens with `POST /auth/sso/exchange`. That only works in the same browser, because of an HttpOnly cookie, which blocks login CSRF through planted links. |
| **Linking an SSO account** | An authenticated `POST /auth/sso/{provider}/link` returns the provider's URL. The old version used a plain link, which can't carry the bearer token, so linking never worked. |
| **Redirects after login** | `?next=` is only followed for same-app paths (`safeNextPath`), so it can't be used as an open redirect. |
| **Showing user data** | Everything goes through Vue's escaping. There is no `v-html` anywhere. Avatar URLs pass through `assetUrl()`, which allows only http(s). Clients can no longer set picture URLs at all; only uploads and SSO imports can. |
| **Content-Security-Policy** (nginx) | Scripts may only come from the app's own origin. Network calls may only go to the app and the Genesis API (`API_ORIGIN`). No framing, no plugins, and forms may only submit to the app itself. Google Fonts were removed so the page makes no third-party requests. |
| **Other headers** (nginx) | HSTS, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`. `index.html` is always revalidated, and only hashed build files are cached long-term. |
| **Forms** | Password rules match the API (12–128 characters, upper and lower case, a number, one of `@#$%^&+=!`), with a confirm field and proper `autocomplete` hints for password managers. Changing your password or email needs your current password. |
| **Admin console** | Buttons are hidden when the API would refuse the action: admins manage regular users, and only root manages admins. Changing a role or disabling an account asks for confirmation. **The API is still what enforces the rules**; the UI only reflects them. |

---

## Libraries

### Runtime (shipped to the browser)

| Library | Version | What it does | Why we use it / benefit |
|---|---|---|---|
| **Vue** | 3.5.44 | Component framework (templates, reactivity) | Templates escape output by default, which blocks most XSS. The Composition and Options APIs, single-file components, and a large ecosystem. |
| **Vue Router** | 4.6.4 | Client-side routes, lazy-loaded views, navigation guards | Each view is loaded as a separate chunk, which keeps the first load small. The guards decide what to show (signed-in pages, admin pages, a `next` after login); the API enforces access. |
| **Vuex** | 4.1.0 | Central state: user, profile, tokens, admin session, auth config | One place for session state and the single shared refresh. *Vuex is in maintenance mode; Pinia is the official replacement* (see follow-ups). |
| **core-js** | 3.50.0 | Polyfills that Babel adds for the browsers listed in `.browserslistrc` | Lets us write modern JavaScript while still supporting the browsers we target. |

The app uses the browser's own `fetch`, `URL`, `URLSearchParams` and `atob`; there's no HTTP client library. That means one less dependency, and requests already respect CORS and `credentials` settings.

### Build and quality tooling (not shipped)

| Library | Version | What it does | Why / benefit |
|---|---|---|---|
| **@vue/cli-service** (+ babel, eslint, router, vuex plugins) | 5.0.9 | `serve`, `build`, `lint` (webpack 5.112 under the hood) | The project's existing build setup. Production builds get content-hashed file names (safe to cache for a long time); source maps are switched **off** (`productionSourceMap: false`). *Vue CLI is in maintenance mode; Vite is recommended* (see follow-ups). |
| **@babel/core**, **@babel/eslint-parser** | 7.29.7, 7.29.9 | Turns modern JavaScript into code for the targeted browsers; lets ESLint parse it | Required by Vue CLI. |
| **ESLint** + **eslint-plugin-vue** | 7.32.0, 8.7.1 | Static checks (`npm run lint`) | Catches mistakes before they ship. *ESLint 7 is end-of-life*; upgrading needs a newer toolchain (Vite + ESLint 9 flat config). |

### Containers

| Image | Purpose | Why |
|---|---|---|
| `node:24-alpine` (build stage) | Runs `npm ci` and `npm run build` | Node 24 is the current LTS; Node 20 reached end of life in April 2026. Alpine keeps the build stage small. |
| `nginx:1.30-alpine` (runtime) | Serves the static build; fills `API_ORIGIN` into the CSP at container start (`/etc/nginx/templates`) | A pinned stable nginx with no Node at runtime. Per-IP rate limiting (`limit_req`) and security headers are set in [`web/nginx.conf.template`](web/nginx.conf.template). |

---

## Configuration

| Name | When | Purpose |
|---|---|---|
| `VUE_APP_API_URL` | Build time (Docker `--build-arg`, or `.env.production` for local builds) | Genesis API base URL compiled into the bundle. The default is `http://localhost:8001`. |
| `API_ORIGIN` | Container start (environment) | The API origin allowed by the CSP's `connect-src`/`img-src`. It must match `VUE_APP_API_URL`'s origin. |

**What the API needs for the web app to work:**
- **`FRONTEND_URL`** on the API must point at this app. SSO hand-off, verification emails and the OIDC consent page all depend on it.
- **This app's origin** must be listed in the API's `CORS_ALLOW_ORIGINS`.
- **For SSO, the app and API must be same-site** (for example `app.example.com` and `auth.example.com`). The SSO cookies are `SameSite=Lax`.

---

## What's outdated, and suggested follow-ups
1. **Vue CLI → Vite and Vuex → Pinia.** Both current tools are in maintenance mode. Moving gives faster builds, a supported toolchain and ESLint 9. This isn't a security fix, so it wasn't part of this round.
2. **HttpOnly refresh-token cookie** so the session survives a reload without exposing tokens to scripts.
3. **Deploy the web app to the homelab cluster** (infra milestone M8). It needs an image build in `build-images.sh`, a Deployment and Ingress, `API_ORIGIN`, and the app's origin in Genesis's CORS list.
4. **Timestamps:** the API returns UTC times without a timezone marker, so the UI shows them shifted by the local offset (for example "8h ago"). Sending timezone-aware ISO strings from the API would fix it.
