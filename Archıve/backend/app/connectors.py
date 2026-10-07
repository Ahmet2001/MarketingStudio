from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

from .config import (
    MOCK_CONNECTIONS,
    PUBLIC_API_URL,
    TIKTOK_CLIENT_KEY,
    TIKTOK_CLIENT_SECRET,
    TOKEN_ENCRYPTION_KEY,
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
)
from .repository import (
    consume_oauth_state,
    disconnect_connection,
    get_connection,
    save_connection,
    save_oauth_state,
)


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    description: str
    scopes: tuple[str, ...]
    authorization_url: str
    token_url: str
    client_id: str
    client_secret: str
    implemented: bool = True

    @property
    def redirect_uri(self) -> str:
        return f"{PUBLIC_API_URL}/api/connections/{self.id}/callback"

    @property
    def available(self) -> bool:
        if not self.implemented:
            return False
        return MOCK_CONNECTIONS or (
            bool(self.client_id)
            and bool(self.client_secret)
            and bool(TOKEN_ENCRYPTION_KEY)
        )

    @property
    def availability_note(self) -> str:
        if not self.implemented:
            return "Publishing connector planned"
        if MOCK_CONNECTIONS:
            return "Mock connection mode"
        if not self.client_id or not self.client_secret:
            return "Add OAuth credentials"
        if not TOKEN_ENCRYPTION_KEY:
            return "Add token encryption key"
        return "Ready to connect"


PROVIDERS: dict[str, Provider] = {
    "youtube": Provider(
        id="youtube",
        name="YouTube",
        description="Prepare uploads for YouTube Shorts and channel publishing.",
        scopes=("https://www.googleapis.com/auth/youtube.upload",),
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
    ),
    "tiktok": Provider(
        id="tiktok",
        name="TikTok",
        description="Connect a TikTok account for future Content Posting API exports.",
        scopes=("user.info.basic", "video.publish"),
        authorization_url="https://www.tiktok.com/v2/auth/authorize/",
        token_url="https://open.tiktokapis.com/v2/oauth/token/",
        client_id=TIKTOK_CLIENT_KEY,
        client_secret=TIKTOK_CLIENT_SECRET,
    ),
    "instagram": Provider(
        id="instagram",
        name="Instagram",
        description="Instagram Reels publishing connection.",
        scopes=(),
        authorization_url="",
        token_url="",
        client_id="",
        client_secret="",
        implemented=False,
    ),
}


def require_provider(provider_id: str) -> Provider:
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        raise KeyError(provider_id)
    return provider


def connection_response(provider: Provider) -> dict:
    stored = get_connection(provider.id)
    connected = bool(stored and stored["status"] == "connected")
    return {
        "provider": provider.id,
        "name": provider.name,
        "description": provider.description,
        "status": "connected" if connected else "disconnected",
        "available": provider.available,
        "availability_note": provider.availability_note,
        "account_label": stored["account_label"] if connected else None,
        "scopes": stored["scopes"] if connected else list(provider.scopes),
        "connected_at": stored["connected_at"] if connected else None,
    }


def list_connections() -> list[dict]:
    return [connection_response(provider) for provider in PROVIDERS.values()]


def build_authorization_url(provider: Provider) -> str:
    if not provider.available:
        raise RuntimeError(provider.availability_note)
    state = token_urlsafe(32)
    save_oauth_state(
        provider.id,
        state,
        datetime.now(UTC) + timedelta(minutes=10),
    )
    if provider.id == "youtube":
        parameters = {
            "client_id": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider.scopes),
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
        }
    else:
        parameters = {
            "client_key": provider.client_id,
            "redirect_uri": provider.redirect_uri,
            "response_type": "code",
            "scope": ",".join(provider.scopes),
            "state": state,
        }
    return f"{provider.authorization_url}?{urlencode(parameters)}"


def _encrypt_tokens(tokens: dict) -> str:
    if not TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("Token encryption is not configured.")
    try:
        cipher = Fernet(TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except ValueError as exc:
        raise RuntimeError("STORYFORGE_TOKEN_ENCRYPTION_KEY is invalid.") from exc
    return cipher.encrypt(json.dumps(tokens).encode("utf-8")).decode("utf-8")


async def complete_oauth(provider: Provider, code: str, state: str) -> dict:
    if not consume_oauth_state(provider.id, state):
        raise ValueError("OAuth state is invalid or expired.")
    if provider.id == "youtube":
        payload = {
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": provider.redirect_uri,
        }
    else:
        payload = {
            "client_key": provider.client_id,
            "client_secret": provider.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": provider.redirect_uri,
        }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(provider.token_url, data=payload)
    if response.is_error:
        raise RuntimeError(
            f"{provider.name} rejected the token exchange ({response.status_code})."
        )
    tokens = response.json()
    scopes_value = tokens.get("scope", "")
    scopes = (
        [value for value in scopes_value.replace(" ", ",").split(",") if value]
        if isinstance(scopes_value, str)
        else list(provider.scopes)
    )
    account_identifier = tokens.get("open_id")
    account_label = (
        f"TikTok · {str(account_identifier)[:10]}"
        if account_identifier
        else f"Connected {provider.name} account"
    )
    save_connection(
        provider.id,
        account_label=account_label,
        encrypted_tokens=_encrypt_tokens(tokens),
        scopes=scopes or list(provider.scopes),
    )
    return connection_response(provider)


def connect_mock(provider: Provider) -> dict:
    if not MOCK_CONNECTIONS:
        raise RuntimeError("Mock connections are disabled.")
    save_connection(
        provider.id,
        account_label=f"Storyforge {provider.name} demo",
        encrypted_tokens=None,
        scopes=list(provider.scopes),
    )
    return connection_response(provider)


def disconnect_provider(provider: Provider) -> dict:
    disconnect_connection(provider.id)
    return connection_response(provider)
