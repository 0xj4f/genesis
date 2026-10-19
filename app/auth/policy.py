"""Who may manage which accounts.

- Everyone may manage their own account (role changes excepted).
- root manages every account except other root accounts.
- admin manages regular users only; anything involving admins is root-only.
"""

from fastapi import HTTPException

from app.utils.audit import security_event

ROLES = ("user", "admin", "root")


def _is_self(actor, target) -> bool:
    return str(actor.id) == str(target.id)


def can_manage(actor, target) -> bool:
    if _is_self(actor, target):
        return True
    if actor.role == "root":
        return target.role != "root"
    if actor.role == "admin":
        return target.role == "user"
    return False


def can_assign_role(actor, target, new_role: str) -> bool:
    # Nobody changes their own role: it prevents self-promotion and a root
    # account demoting itself out of existence.
    if new_role not in ROLES or _is_self(actor, target) or not can_manage(actor, target):
        return False
    if actor.role == "root":
        return True
    # Admins may manage users, but promoting to (or from) admin is root-only.
    return actor.role == "admin" and target.role == "user" and new_role == "user"


def deny(actor, action: str, target_id: str | None = None):
    security_event("authz_denied", actor=str(actor.id), role=actor.role, action=action, target=target_id)
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def ensure_can_manage(actor, target, action: str) -> None:
    if not can_manage(actor, target):
        deny(actor, action, str(target.id))
