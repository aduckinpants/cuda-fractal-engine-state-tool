from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


OPENAI_CREDENTIAL_TARGET = "openai/api_key"
OPENAI_CREDENTIAL_USERNAME = "api_key"
OPENAI_LEGACY_CREDENTIAL_USERNAME = "OPENAI_API_KEY"


class CredentialStore(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...

    def set_password(self, service: str, username: str, password: str) -> None: ...

    def delete_password(self, service: str, username: str) -> None: ...


@dataclass(frozen=True)
class OpenAICredential:
    value: str = field(repr=False)
    source: str

    @property
    def fingerprint_sha256(self) -> str:
        """Return a comparison identity without persisting the credential."""

        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()

    @property
    def key_kind(self) -> str:
        if self.value.startswith("sk-proj-"):
            return "project_scoped"
        if self.value.startswith("sk-svcacct-"):
            return "service_account"
        return "other"

    def identity_dict(self) -> dict[str, Any]:
        return {
            "credential_identity_version": 1,
            "source": self.source,
            "key_kind": self.key_kind,
            "fingerprint_sha256_prefix": self.fingerprint_sha256[:16],
        }


def _default_store() -> CredentialStore:
    try:
        import keyring
    except ImportError as exc:  # pragma: no cover - packaging guard
        raise RuntimeError("The keyring package is required for Windows Credential Manager") from exc
    return keyring


def resolve_openai_api_key(
    *,
    environment: Mapping[str, str] | None = None,
    store: CredentialStore | None = None,
) -> OpenAICredential | None:
    values = os.environ if environment is None else environment
    environment_value = values.get("OPENAI_API_KEY", "").strip()
    if environment_value:
        return OpenAICredential(environment_value, "environment:OPENAI_API_KEY")
    credential_store = store or _default_store()
    credential_value = credential_store.get_password(
        OPENAI_CREDENTIAL_TARGET,
        OPENAI_CREDENTIAL_USERNAME,
    )
    if credential_value and credential_value.strip():
        return OpenAICredential(credential_value.strip(), "windows_credential_manager")
    legacy_value = credential_store.get_password(
        OPENAI_CREDENTIAL_TARGET,
        OPENAI_LEGACY_CREDENTIAL_USERNAME,
    )
    if legacy_value and legacy_value.strip():
        return OpenAICredential(
            legacy_value.strip(),
            "windows_credential_manager:legacy_username",
        )
    return None


def set_openai_api_key(value: str, *, store: CredentialStore | None = None) -> None:
    normalized = value.strip()
    if not normalized:
        raise ValueError("OpenAI API key cannot be empty")
    if any(character in normalized for character in "\r\n\x00"):
        raise ValueError("OpenAI API key contains an invalid control character")
    (store or _default_store()).set_password(
        OPENAI_CREDENTIAL_TARGET,
        OPENAI_CREDENTIAL_USERNAME,
        normalized,
    )


def delete_openai_api_key(*, store: CredentialStore | None = None) -> None:
    target = store or _default_store()
    for username in (OPENAI_CREDENTIAL_USERNAME, OPENAI_LEGACY_CREDENTIAL_USERNAME):
        try:
            target.delete_password(OPENAI_CREDENTIAL_TARGET, username)
        except Exception as exc:
            # keyring backends use backend-specific exceptions for an absent credential.
            if exc.__class__.__name__ not in {
                "PasswordDeleteError",
                "CredentialNotFoundError",
            }:
                raise
