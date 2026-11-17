"""Bounded JSON security events. Callers pass IDs/enums, never credentials.

The mutable request context intentionally crosses FastAPI's threadpool boundary;
ContextVar.set() inside a sync dependency would not propagate back to middleware.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import stat
import sys
import time
from uuid import uuid4

audit_context: ContextVar[dict | None] = ContextVar("security_context", default=None)
security_log = logging.getLogger("genesis.security")
security_log.propagate = False
security_log.setLevel(logging.INFO)
security_log.addHandler(logging.NullHandler())

# Extra fields are deliberately allowlisted. Do not add arbitrary request data.
FIELDS = {"user_id", "actor", "target", "role", "action", "old", "new", "subject",
          "client_id", "provider", "method", "purpose", "reason", "status", "count",
          "generated", "queued", "account_request"}
FAILED = {"login_failed", "reauth_failed", "client_auth_failed", "authz_denied",
          "login_throttled", "refresh_client_mismatch", "refresh_replay_detected",
          "oauth_consent_denied", "request_rejected", "request_failed", "cli_failed",
          "startup_failed", "account_locked", "sso_failed"}


def subject_hash(value: str) -> str:
    """Correlation only, never proof of identity (nor anonymization)."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:16]


def _safe(value, limit=128):
    if value is None or isinstance(value, (int, bool)):
        return value
    if not isinstance(value, str):
        return "<invalid>"
    return "".join(c if c.isprintable() else "?" for c in value[:limit])


def identify_actor(actor_id: str, *, kind="user", role=None):
    """Only call after authentication; never trust unverified JWT claims."""
    context = audit_context.get()
    if context is not None:
        context["actor"] = {"type": kind, "id": _safe(actor_id), "role": _safe(role)}


def security_event(event: str, **fields) -> None:
    context = audit_context.get() or {}
    scope = context.get("scope", {})
    route = scope.get("route")
    actor = context.get("actor", {"type": "anonymous" if scope else "service", "id": None if scope else "genesis-iam", "role": None})
    if fields.get("actor"):
        role = fields.get("role", actor.get("role") if actor.get("id") == fields["actor"] else None)
        actor = {"type": "user", "id": _safe(fields["actor"]), "role": _safe(role)}
    # user_id is the SUBJECT, not necessarily the actor (e.g. email resend).
    failed = event in FAILED
    record = {
        "schema_version": 1,
        "event_id": str(uuid4()),
        "when": {"timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                 "request_id": context.get("request_id")},
        "who": {**actor, "source_ip": _safe(scope.get("client")[0] if scope.get("client") else None)},
        "where": {"service": "genesis-iam", "instance": _safe(socket.gethostname()),
                  "pid": os.getpid(), "method": _safe(scope.get("method")),
                  "route": _safe(getattr(route, "path", "<unmatched>") if scope else context.get("entrypoint", "process"))},
        "what": {"event": _safe(event), "outcome": "failure" if failed else "success",
                 "severity": "error" if event in {"request_failed", "startup_failed"} else "warning" if failed else "info",
                 "details": {key: _safe(value) for key, value in fields.items() if key in FIELDS and value is not None}},
    }
    message = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
    if len(message.encode("utf-8")) >= 8192:
        record["what"]["details"] = {"reason": "event_fields_exceeded_limit"}
        message = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
    security_log.info(message)


class SecurityFileHandler(logging.Handler):
    """Byte-bounded rename ring, synchronized with concurrent CLI writers.

    Reopen for every append under a stable lock: no process keeps a stale inode
    after another writer rotates. O_NOFOLLOW rejects final-component symlinks.
    Failure is fail-open with a rate-limited, credential-free stderr alarm.
    """

    def __init__(self, path, total_mib=50, *, segment_bytes=10 * 1024 * 1024):
        super().__init__()
        self.path = Path(path)
        self.segment_bytes = segment_bytes
        self.files = total_mib * 1024 * 1024 // segment_bytes
        if self.files < 2:
            raise ValueError("Security log budget must hold at least two segments")
        self.last_error = float("-inf")
        self.failures = 0

    @staticmethod
    def _open(path, flags):
        fd = os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o640)
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise OSError("Security log must be a regular, singly-linked file")
            os.fchmod(fd, 0o640)
            return fd
        except Exception:
            os.close(fd)
            raise

    def emit(self, record):
        try:
            data = (self.format(record) + "\n").encode("utf-8")
            if len(data) > min(8192, self.segment_bytes):
                raise ValueError("Oversized security event")
            # Provision the parent in deployment; never create /var/log ourselves.
            lock = self._open(self.path.with_name(".security.log.lock"), os.O_CREAT | os.O_RDWR)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX)
                for old in self.path.parent.glob(self.path.name + ".*"):
                    suffix = old.name.removeprefix(self.path.name + ".")
                    if suffix.isdigit() and int(suffix) >= self.files:
                        old.unlink()
                fd = self._open(self.path, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
                try:
                    if os.fstat(fd).st_size + len(data) > self.segment_bytes:
                        os.close(fd)
                        fd = None
                        for index in range(self.files - 1, 0, -1):
                            source = self.path if index == 1 else Path(f"{self.path}.{index - 1}")
                            if source.exists():
                                source.replace(f"{self.path}.{index}")
                        fd = self._open(self.path, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
                    original_size = os.fstat(fd).st_size
                    try:
                        view = memoryview(data)
                        while view:
                            written = os.write(fd, view)
                            if not written:
                                raise OSError("Short security log write")
                            view = view[written:]
                    except Exception:
                        # ENOSPC can follow a partial write. Remove the fragment
                        # so recovery cannot concatenate two different events.
                        os.ftruncate(fd, original_size)
                        raise
                finally:
                    if fd is not None:
                        os.close(fd)
            finally:
                os.close(lock)
        except Exception:
            self.handleError(record)

    def handleError(self, record):
        self.failures += 1
        now = time.monotonic()
        if now - self.last_error >= 60:
            self.last_error = now
            try:
                sys.stderr.write("SECURITY_LOG_WRITE_FAILED: security events are being lost; check log volume and permissions.\n")
            except Exception:
                pass


def configure_security_logging(settings):
    security_log.disabled = False
    for handler in security_log.handlers[:]:
        security_log.removeHandler(handler)
        handler.close()
    security_log.addHandler(SecurityFileHandler(settings.SECURITY_LOG_PATH, settings.SECURITY_LOG_TOTAL_MIB))
