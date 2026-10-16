"""Apply limits before request parsing, database access, or password hashing."""

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from app.utils.security_store import get_security_store, SecurityStoreUnavailable


class SecurityMiddleware:
    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Cache-Control"] = "no-store"
                if scope.get("scheme") == "https":
                    headers["Strict-Transport-Security"] = "max-age=31536000"
            await send(message)

        async def reject(status, detail, headers=None):
            await JSONResponse({"detail": detail}, status_code=status, headers=headers)(scope, receive, secure_send)

        # Use the transport peer (or Uvicorn's explicitly trusted proxy result).
        # Never parse client-supplied forwarding headers here.
        ip = scope["client"][0] if scope.get("client") else "unknown"
        path = scope["path"].rstrip("/")
        limits = [(f"ip:{ip}", self.settings.RATE_LIMIT_PER_SECOND, 1)]
        if scope["method"] == "POST" and path in {"/token", "/admin/login", "/users", "/oauth/token"}:
            limits.append((f"auth:{ip}", self.settings.AUTH_RATE_LIMIT_PER_MINUTE, 60))
        elif scope["method"] == "POST" and path == "/refresh_token":
            limits.append((f"refresh:{ip}", self.settings.REFRESH_RATE_LIMIT_PER_MINUTE, 60))
        elif scope["method"] == "GET" and path.startswith("/auth/sso/") and path.endswith(("/authorize", "/link", "/callback")):
            limits.append((f"auth:{ip}", self.settings.AUTH_RATE_LIMIT_PER_MINUTE, 60))

        try:
            store = get_security_store()
            for key, limit, window in limits:
                retry = store.check_rate(key, limit, window)
                if retry:
                    return await reject(429, "Too many requests", {"Retry-After": str(retry)})
        except SecurityStoreUnavailable:
            return await reject(503, "Security service temporarily unavailable", {"Retry-After": "5"})

        lengths = [value for name, value in scope["headers"] if name == b"content-length"]
        if lengths:
            try:
                length = int(lengths[0])
            except ValueError:
                return await reject(400, "Invalid Content-Length")
            if len(lengths) != 1 or length < 0:
                return await reject(400, "Invalid Content-Length")
            if length > self.settings.MAX_REQUEST_BODY_BYTES:
                return await reject(413, "Request body too large")

        # Bound actual bytes too: Content-Length may be absent (chunked requests)
        # or untruthful. Buffer only up to the configured upload allowance.
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.settings.MAX_REQUEST_BODY_BYTES:
                return await reject(413, "Request body too large")
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, secure_send)
