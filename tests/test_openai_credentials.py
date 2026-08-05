from __future__ import annotations

import hashlib
import unittest

from cuda_fractal_state_tool.openai_credentials import (
    OPENAI_CREDENTIAL_TARGET,
    OPENAI_CREDENTIAL_USERNAME,
    OPENAI_LEGACY_CREDENTIAL_USERNAME,
    delete_openai_api_key,
    resolve_openai_api_key,
    set_openai_api_key,
)


class FakeCredentialStore:
    def __init__(
        self,
        value: str | None = None,
        *,
        legacy_value: str | None = None,
    ) -> None:
        self.values = {
            OPENAI_CREDENTIAL_USERNAME: value,
            OPENAI_LEGACY_CREDENTIAL_USERNAME: legacy_value,
        }
        self.calls: list[tuple[str, ...]] = []

    def get_password(self, service: str, username: str) -> str | None:
        self.calls.append(("get", service, username))
        return self.values.get(username)

    def set_password(self, service: str, username: str, password: str) -> None:
        self.calls.append(("set", service, username, password))
        self.values[username] = password

    def delete_password(self, service: str, username: str) -> None:
        self.calls.append(("delete", service, username))
        self.values[username] = None


class OpenAICredentialTests(unittest.TestCase):
    def test_environment_precedes_windows_credential_manager(self) -> None:
        store = FakeCredentialStore("stored-key")
        credential = resolve_openai_api_key(
            environment={"OPENAI_API_KEY": " environment-key "},
            store=store,
        )
        self.assertEqual(credential.value, "environment-key")
        self.assertEqual(credential.source, "environment:OPENAI_API_KEY")
        self.assertEqual(store.calls, [])

    def test_stored_key_and_missing_key_are_explicit(self) -> None:
        store = FakeCredentialStore(" stored-key ")
        credential = resolve_openai_api_key(environment={}, store=store)
        self.assertEqual(credential.value, "stored-key")
        self.assertEqual(credential.source, "windows_credential_manager")
        store.values[OPENAI_CREDENTIAL_USERNAME] = None
        self.assertIsNone(resolve_openai_api_key(environment={}, store=store))

    def test_identity_is_comparable_without_exposing_the_key(self) -> None:
        credential = resolve_openai_api_key(
            environment={"OPENAI_API_KEY": "sk-proj-secret-value"},
            store=FakeCredentialStore(),
        )
        self.assertEqual(
            credential.identity_dict(),
            {
                "credential_identity_version": 1,
                "source": "environment:OPENAI_API_KEY",
                "key_kind": "project_scoped",
                "fingerprint_sha256_prefix": hashlib.sha256(
                    b"sk-proj-secret-value"
                ).hexdigest()[:16],
            },
        )
        self.assertNotIn("sk-proj-secret-value", repr(credential))
        self.assertNotIn("value", credential.identity_dict())

        service = resolve_openai_api_key(
            environment={"OPENAI_API_KEY": "sk-svcacct-secret-value"},
            store=FakeCredentialStore(),
        )
        self.assertEqual(service.key_kind, "service_account")

    def test_legacy_windows_username_is_read_only_fallback(self) -> None:
        store = FakeCredentialStore(legacy_value=" legacy-key ")
        credential = resolve_openai_api_key(environment={}, store=store)
        self.assertEqual(credential.value, "legacy-key")
        self.assertEqual(
            credential.source,
            "windows_credential_manager:legacy_username",
        )
        self.assertEqual(
            store.calls,
            [
                ("get", OPENAI_CREDENTIAL_TARGET, OPENAI_CREDENTIAL_USERNAME),
                ("get", OPENAI_CREDENTIAL_TARGET, OPENAI_LEGACY_CREDENTIAL_USERNAME),
            ],
        )

        store = FakeCredentialStore("primary-key", legacy_value="legacy-key")
        credential = resolve_openai_api_key(environment={}, store=store)
        self.assertEqual(credential.value, "primary-key")
        self.assertEqual(credential.source, "windows_credential_manager")

    def test_set_and_delete_use_exact_target_without_exposing_value(self) -> None:
        store = FakeCredentialStore()
        set_openai_api_key(" sk-test-value ", store=store)
        self.assertEqual(
            store.calls[-1],
            ("set", OPENAI_CREDENTIAL_TARGET, OPENAI_CREDENTIAL_USERNAME, "sk-test-value"),
        )
        delete_openai_api_key(store=store)
        self.assertEqual(
            store.calls[-2:],
            [
                ("delete", OPENAI_CREDENTIAL_TARGET, OPENAI_CREDENTIAL_USERNAME),
                (
                    "delete",
                    OPENAI_CREDENTIAL_TARGET,
                    OPENAI_LEGACY_CREDENTIAL_USERNAME,
                ),
            ],
        )

    def test_set_rejects_empty_or_multiline_values(self) -> None:
        store = FakeCredentialStore()
        for value in ("", "  ", "sk-line\nsecond"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                set_openai_api_key(value, store=store)


if __name__ == "__main__":
    unittest.main()
