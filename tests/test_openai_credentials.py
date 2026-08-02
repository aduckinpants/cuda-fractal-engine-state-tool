from __future__ import annotations

import unittest

from cuda_fractal_state_tool.openai_credentials import (
    OPENAI_CREDENTIAL_TARGET,
    OPENAI_CREDENTIAL_USERNAME,
    delete_openai_api_key,
    resolve_openai_api_key,
    set_openai_api_key,
)


class FakeCredentialStore:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.calls: list[tuple[str, ...]] = []

    def get_password(self, service: str, username: str) -> str | None:
        self.calls.append(("get", service, username))
        return self.value

    def set_password(self, service: str, username: str, password: str) -> None:
        self.calls.append(("set", service, username, password))
        self.value = password

    def delete_password(self, service: str, username: str) -> None:
        self.calls.append(("delete", service, username))
        self.value = None


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
        store.value = None
        self.assertIsNone(resolve_openai_api_key(environment={}, store=store))

    def test_set_and_delete_use_exact_target_without_exposing_value(self) -> None:
        store = FakeCredentialStore()
        set_openai_api_key(" sk-test-value ", store=store)
        self.assertEqual(
            store.calls[-1],
            ("set", OPENAI_CREDENTIAL_TARGET, OPENAI_CREDENTIAL_USERNAME, "sk-test-value"),
        )
        delete_openai_api_key(store=store)
        self.assertEqual(
            store.calls[-1],
            ("delete", OPENAI_CREDENTIAL_TARGET, OPENAI_CREDENTIAL_USERNAME),
        )

    def test_set_rejects_empty_or_multiline_values(self) -> None:
        store = FakeCredentialStore()
        for value in ("", "  ", "sk-line\nsecond"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                set_openai_api_key(value, store=store)


if __name__ == "__main__":
    unittest.main()
