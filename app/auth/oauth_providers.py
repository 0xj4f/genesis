"""OAuth2 provider configurations for Google, GitHub, and Facebook SSO."""

from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()

PROVIDERS: dict[str, "OAuthProviderConfig"] = {}


@dataclass
class OAuthProviderConfig:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]
    redirect_uri: str

    # Mapping from provider userinfo fields to our internal fields
    field_map: dict[str, str] = None

    def __post_init__(self):
        if self.field_map is None:
            self.field_map = {}


def _register_providers():
    """Register all configured providers. Called at module load."""

    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        PROVIDERS["google"] = OAuthProviderConfig(
            name="google",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scopes=["openid", "email", "profile"],
            redirect_uri=settings.GOOGLE_REDIRECT_URI or f"{settings.OAUTH_ISSUER}/auth/sso/google/callback",
            field_map={
                "sub": "sub",
                "email": "email",
                "email_verified": "email_verified",
                "name": "name",
                "given_name": "given_name",
                "family_name": "family_name",
                "picture": "picture",
            },
        )

    if settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET:
        PROVIDERS["github"] = OAuthProviderConfig(
            name="github",
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=["read:user", "user:email"],
            redirect_uri=settings.GITHUB_REDIRECT_URI or f"{settings.OAUTH_ISSUER}/auth/sso/github/callback",
            field_map={
                "sub": "id",
                "email": "email",
                "name": "name",
                "picture": "avatar_url",
                "username": "login",
            },
        )

    if settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET:
        PROVIDERS["facebook"] = OAuthProviderConfig(
            name="facebook",
            client_id=settings.FACEBOOK_CLIENT_ID,
            client_secret=settings.FACEBOOK_CLIENT_SECRET,
            authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
            token_url="https://graph.facebook.com/v19.0/oauth/access_token",
            userinfo_url="https://graph.facebook.com/me?fields=id,name,email,picture.type(large)",
            scopes=["email", "public_profile"],
            redirect_uri=settings.FACEBOOK_REDIRECT_URI or f"{settings.OAUTH_ISSUER}/auth/sso/facebook/callback",
            field_map={
                "sub": "id",
                "email": "email",
                "name": "name",
                "picture": "picture.data.url",
            },
        )


_register_providers()


def get_provider(name: str) -> OAuthProviderConfig:
    """Get a provider config by name. Raises ValueError if not configured."""
    provider = PROVIDERS.get(name)
    if not provider:
        configured = list(PROVIDERS.keys()) or ["none"]
        raise ValueError(
            f"SSO provider '{name}' is not configured. "
            f"Configured providers: {', '.join(configured)}"
        )
    return provider


def list_providers() -> list[str]:
    """Return names of all configured providers."""
    return list(PROVIDERS.keys())
