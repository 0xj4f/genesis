"""CLI management commands for Genesis IAM.

Usage:
    python -m app.cli generate-keys                 Generate dev RSA key pair
    python -m app.cli rotate-keys                   Rotate signing key (DB-backed)
    python -m app.cli create-client NAME             Register an OAuth client
    python -m app.cli reset-password USERNAME        Emergency password reset (reads stdin)
"""
import argparse
import getpass
import os
import sys
import secrets

from app.auth.keys import generate_rsa_key_pair


def cmd_generate_keys(args):
    """Generate RSA key pair for development."""
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    private_path = os.path.join(output_dir, "dev-private.pem")
    public_path = os.path.join(output_dir, "dev-public.pem")

    if os.path.exists(private_path) and not args.force:
        print(f"Keys already exist at {output_dir}. Use --force to overwrite.")
        sys.exit(1)

    private_pem, public_pem = generate_rsa_key_pair(key_size=args.key_size)

    with open(private_path, "wb") as f:
        f.write(private_pem)
    os.chmod(private_path, 0o600)
    with open(public_path, "wb") as f:
        f.write(public_pem)

    print(f"RSA {args.key_size}-bit key pair generated:")
    print(f"  Private: {private_path}")
    print(f"  Public:  {public_path}")
    print()
    print("Add to your .env:")
    print(f"  OAUTH_PRIVATE_KEY_PATH={private_path}")
    print(f"  OAUTH_PUBLIC_KEY_PATH={public_path}")


def cmd_rotate_keys(args):
    """Rotate signing keys in the database."""
    print("Key rotation via database is not yet implemented.")
    print("For file-based keys, generate a new pair with 'generate-keys' and update .env paths.")


def cmd_create_client(args):
    """Register a new OAuth client in the database."""
    from app.database.session import SessionLocal
    from app.database.oauth_client_db_interface import create_oauth_client_db, get_oauth_client_by_name_db
    from app.utils.security import hash_client_secret

    db = SessionLocal()
    try:
        existing = get_oauth_client_by_name_db(db, args.name)
        if existing:
            print(f"Client '{args.name}' already exists (id={existing.id})")
            sys.exit(1)

        # Generate client secret
        client_secret = secrets.token_urlsafe(32)
        client_secret_hash = hash_client_secret(client_secret)

        redirect_uris = [u.strip() for u in args.redirect_uris.split(",")]
        scopes = [s.strip() for s in args.scopes.split(",")]
        audiences = [a.strip() for a in args.audiences.split(",")]
        grant_types = [g.strip() for g in args.grant_types.split(",")]

        client = create_oauth_client_db(db, {
            "client_secret_hash": client_secret_hash,
            "client_name": args.name,
            "redirect_uris": redirect_uris,
            "allowed_scopes": scopes,
            "allowed_audiences": audiences,
            "grant_types": grant_types,
            "is_active": True,
            "is_confidential": not args.public,
            "is_first_party": args.first_party,
        })

        print(f"OAuth client created:")
        print(f"  client_id:     {client.id}")
        print(f"  client_secret: {client_secret}")
        print(f"  name:          {client.client_name}")
        print(f"  redirect_uris: {redirect_uris}")
        print(f"  scopes:        {scopes}")
        print(f"  audiences:     {audiences}")
        print(f"  grant_types:   {grant_types}")
        print(f"  confidential:  {client.is_confidential}")
        print(f"  first-party:   {client.is_first_party}")
        print()
        print("IMPORTANT: Save the client_secret now. It cannot be retrieved later.")
    finally:
        db.close()


def cmd_reset_password(args):
    """Break-glass password reset for an account (e.g. after a rollback).

    The new password is read from stdin (or an interactive prompt) and is never
    printed. All of the account's sessions are revoked.
    """
    from app.database.session import SessionLocal
    from app.database.user_db_interface import get_user_by_username_db, set_user_password_db
    from app.models.user_api_model import validate_password_strength
    from app.utils.security import hash_password

    if sys.stdin.isatty():
        password = getpass.getpass("New password: ")
        if getpass.getpass("Repeat new password: ") != password:
            print("Passwords do not match.")
            sys.exit(1)
    else:
        password = sys.stdin.readline().rstrip("\n")
    try:
        validate_password_strength(password)
    except ValueError as e:
        print(f"Rejected: {e}")
        sys.exit(1)

    db = SessionLocal()
    try:
        user = get_user_by_username_db(db, args.username)
        if not user:
            print(f"No user named '{args.username}'.")
            sys.exit(1)
        set_user_password_db(db, user, hash_password(password), reason="cli_password_reset")
        print(f"Password reset for '{args.username}'. All sessions were revoked.")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Genesis IAM CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate-keys
    gen_parser = subparsers.add_parser("generate-keys", help="Generate RSA key pair for development")
    gen_parser.add_argument("--output-dir", default="./secrets", help="Output directory (default: ./secrets)")
    gen_parser.add_argument("--key-size", type=int, default=2048, help="RSA key size (default: 2048)")
    gen_parser.add_argument("--force", action="store_true", help="Overwrite existing keys")
    gen_parser.set_defaults(func=cmd_generate_keys)

    # rotate-keys
    rot_parser = subparsers.add_parser("rotate-keys", help="Rotate signing key")
    rot_parser.set_defaults(func=cmd_rotate_keys)

    # create-client
    client_parser = subparsers.add_parser("create-client", help="Register an OAuth client")
    client_parser.add_argument("name", help="Client name")
    client_parser.add_argument("--redirect-uris", default="http://localhost:3000/callback", help="Comma-separated redirect URIs")
    client_parser.add_argument("--scopes", default="openid,profile,email,offline_access", help="Comma-separated allowed scopes")
    client_parser.add_argument("--audiences", default="genesis-api", help="Comma-separated allowed audiences")
    client_parser.add_argument("--grant-types", default="authorization_code,refresh_token", help="Comma-separated grant types")
    client_parser.add_argument("--public", action="store_true", help="Create as public client (no secret required, PKCE mandatory)")
    client_parser.add_argument("--first-party", action="store_true", help="Skip the consent screen (only for clients you operate)")
    client_parser.set_defaults(func=cmd_create_client)

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Emergency password reset (password read from stdin)")
    reset_parser.add_argument("username", help="Account username")
    reset_parser.set_defaults(func=cmd_reset_password)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
