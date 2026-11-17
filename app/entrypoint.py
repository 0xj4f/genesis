"""Shell-free container startup. One worker owns the in-memory security state."""

import os
from pathlib import Path
import socket
import sys
import time


def wait_for_db(host, port, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(2)
    raise RuntimeError("Database did not become ready")


def main():
    os.umask(0o027)
    from app.config import get_settings
    from app.utils.audit import configure_security_logging, security_event
    settings = get_settings()
    configure_security_logging(settings)
    security_event("startup_started")
    try:
        from app.auth.keys import generate_rsa_key_pair, get_signing_key
        private = Path(settings.OAUTH_PRIVATE_KEY_PATH) if settings.OAUTH_PRIVATE_KEY_PATH else None
        public = Path(settings.OAUTH_PUBLIC_KEY_PATH) if settings.OAUTH_PUBLIC_KEY_PATH else None
        if private and public and not private.exists() and not public.exists():
            # Mounted, provisioned keys (Helm) are used unchanged. Standalone
            # Compose persists its generated pair in an explicitly writable volume.
            private.parent.mkdir(parents=True, exist_ok=True)
            public.parent.mkdir(parents=True, exist_ok=True)
            private_pem, public_pem = generate_rsa_key_pair()
            with private.open("xb") as stream:
                os.chmod(private, 0o600)
                stream.write(private_pem)
            with public.open("xb") as stream:
                stream.write(public_pem)
            security_event("signing_keys_generated")
        get_signing_key()
        wait_for_db(settings.DATABASE_HOST, settings.DATABASE_PORT)
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config("/app/alembic.ini"), "head")
        from app.database.seed import seed_adam
        seed_adam()
        # SERVICES -> services table, plus pending memberships for accounts that lack one.
        from app.services.membership_service import sync_services
        sync_services()
    except Exception:
        security_event("startup_failed")
        raise

    # Exec keeps Uvicorn as PID 1 and preserves signal handling. Access logs are
    # disabled: default Uvicorn access logs include OAuth query-string secrets.
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "0.0.0.0", "--port", "8000", "--workers", "1",
             "--no-access-log", "--no-server-header", "--forwarded-allow-ips",
             os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")])


if __name__ == "__main__":
    main()
