"""Security event logging. Never pass passwords, tokens or secrets here."""

import hashlib
import logging

security_log = logging.getLogger("genesis.security")


def subject_hash(value: str) -> str:
    """Short, stable identifier for a submitted username or email that may not
    belong to any account (and may be a mistyped password)."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()[:16]


def security_event(event: str, **fields) -> None:
    details = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    security_log.info("%s %s", event, details)
