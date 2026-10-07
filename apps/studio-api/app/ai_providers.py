from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .config import RUNTIME_ROOT, TOKEN_ENCRYPTION_KEY, ensure_runtime_directories
from .repository import (
    delete_ai_provider_credential,
    get_ai_provider_credential,
    save_ai_provider_credential,
)


@dataclass(frozen=True)
class AiProvider:
    id: str
    name: str
    description: str
    environment_variable: str


AI_PROVIDERS: dict[str, AiProvider] = {
    "replicate": AiProvider(
        id="replicate",
        name="Replicate",
        description="Run official and community image models from Replicate.",
        environment_variable="REPLICATE_API_TOKEN",
    ),
    "fal": AiProvider(
        id="fal",
        name="fal.ai",
        description="Run fast generative media models through fal model APIs.",
        environment_variable="FAL_KEY",
    ),
    "together": AiProvider(
        id="together",
        name="Together AI",
        description="Generate images with Together AI serverless image models.",
        environment_variable="TOGETHER_API_KEY",
    ),
    "gemini": AiProvider(
        id="gemini",
        name="Google Gemini",
        description=(
            "Generate native images with Gemini. An API key is required and "
            "image models may require billing."
        ),
        environment_variable="GEMINI_API_KEY",
    ),
}


def require_ai_provider(provider_id: str) -> AiProvider:
    provider = AI_PROVIDERS.get(provider_id)
    if provider is None:
        raise KeyError(provider_id)
    return provider


def _local_key_path() -> Path:
    return RUNTIME_ROOT / ".credentials.key"


def _encryption_key() -> bytes:
    if TOKEN_ENCRYPTION_KEY:
        return TOKEN_ENCRYPTION_KEY.encode("utf-8")
    ensure_runtime_directories()
    path = _local_key_path()
    if path.is_file():
        return path.read_bytes().strip()
    key = Fernet.generate_key()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(key)
    return key


def _cipher() -> Fernet:
    try:
        return Fernet(_encryption_key())
    except ValueError as exc:
        raise RuntimeError("The Storyforge credential encryption key is invalid.") from exc


def save_api_key(provider_id: str, api_key: str) -> dict:
    provider = require_ai_provider(provider_id)
    encrypted = _cipher().encrypt(api_key.encode("utf-8")).decode("utf-8")
    hint = f"••••••••{api_key[-4:]}"
    return save_ai_provider_credential(
        provider.id,
        encrypted_api_key=encrypted,
        key_hint=hint,
    )


def get_api_key(provider_id: str) -> str | None:
    provider = require_ai_provider(provider_id)
    stored = get_ai_provider_credential(provider.id)
    if stored is not None:
        try:
            return _cipher().decrypt(
                stored["encrypted_api_key"].encode("utf-8")
            ).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError(
                f"The saved {provider.name} credential cannot be decrypted."
            ) from exc
    return os.getenv(provider.environment_variable) or None


def provider_response(provider: AiProvider) -> dict:
    stored = get_ai_provider_credential(provider.id)
    environment_value = os.getenv(provider.environment_variable)
    configured = stored is not None or bool(environment_value)
    key_hint = stored["key_hint"] if stored else (
        f"Environment · ••••{environment_value[-4:]}"
        if environment_value
        else None
    )
    return {
        "provider": provider.id,
        "name": provider.name,
        "description": provider.description,
        "configured": configured,
        "key_hint": key_hint,
        "updated_at": stored["updated_at"] if stored else None,
    }


def list_ai_providers() -> list[dict]:
    return [provider_response(provider) for provider in AI_PROVIDERS.values()]


def delete_api_key(provider_id: str) -> dict:
    provider = require_ai_provider(provider_id)
    delete_ai_provider_credential(provider.id)
    return provider_response(provider)
