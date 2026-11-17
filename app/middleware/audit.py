"""Request attribution, including rejections before routing/authentication."""

from uuid import UUID, uuid4
from app.utils.audit import audit_context, security_event, subject_hash


class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        context = {"scope": scope, "request_id": str(uuid4())}
        token = audit_context.set(context)
        status = 500

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        except Exception:
            status = 500
            raise
        finally:
            try:
                route = getattr(scope.get("route"), "path", "")
                role = context.get("actor", {}).get("role")
                target = None
                for key in ("user_id", "client_id", "session_id"):
                    value = scope.get("path_params", {}).get(key)
                    if value is not None:
                        try:
                            value = str(UUID(str(value)))
                            target = subject_hash(value) if key == "session_id" else value
                        except ValueError:
                            pass
                        break
                if status >= 400:
                    security_event("request_failed" if status >= 500 else "request_rejected", status=status, target=target)
                elif route and (scope["method"] in {"POST", "PUT", "PATCH", "DELETE"} or role in {"root", "admin"}):
                    security_event("privileged_access" if role in {"root", "admin"} else "security_operation", status=status, target=target)
            finally:
                audit_context.reset(token)
