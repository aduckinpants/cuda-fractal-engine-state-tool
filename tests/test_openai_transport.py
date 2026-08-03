from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import AgentBundleHandoff
from cuda_fractal_state_tool.automated_run_store import AutomatedRunStore
from cuda_fractal_state_tool.openai_transport import (
    AmbiguousRemoteCompletion,
    DispatchAuthorizationRejected,
    PacketV8ResponsesTransport,
    ProviderFailureKind,
    ProviderFile,
    ProviderResponse,
    ProviderTransportError,
    TransportCancelled,
    classify_provider_failure,
    prepare_packet_transport,
    sanitize_evidence,
)
from cuda_fractal_state_tool.workspace_layout import initialize_workspace_root


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


class FakeProvider:
    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []
        self.requests: list[dict[str, object]] = []
        self.response_error: Exception | None = None
        self.response_status = "completed"
        self.on_response = None
        self.count_requests: list[dict[str, object]] = []

    def upload_file(self, filename: str, payload: bytes) -> ProviderFile:
        self.uploaded.append(filename)
        return ProviderFile(id=f"file-{filename}", filename=filename)

    def create_response(self, request, *, timeout_seconds: float) -> ProviderResponse:
        self.requests.append({"request": request, "timeout_seconds": timeout_seconds})
        if self.on_response is not None:
            self.on_response()
        if self.response_error is not None:
            raise self.response_error
        return ProviderResponse(
            id="resp-1",
            model="gpt-5.6-2026-07-01",
            status=self.response_status,
            output_text="A grounded response.",
            usage={
                "input_tokens": 123,
                "cached_input_tokens": 23,
                "cache_write_tokens": 17,
                "output_tokens": 45,
            },
            raw={
                "id": "resp-1",
                "model": "gpt-5.6-2026-07-01",
                "output_text": "A grounded response.",
                "usage": {
                    "input_tokens": 123,
                    "input_tokens_details": {
                        "cached_tokens": 23,
                        "cache_write_tokens": 17,
                    },
                    "output_tokens": 45,
                },
            },
        )

    def count_input_tokens(self, request, *, timeout_seconds: float) -> int:
        self.count_requests.append({"request": request, "timeout_seconds": timeout_seconds})
        return 123

    def delete_file(self, file_id: str) -> None:
        self.deleted.append(file_id)


class PacketFixture:
    def __init__(self, root: Path) -> None:
        self.packet_dir = root / "packet-v8"
        self.packet_dir.mkdir()
        self.payloads = {
            "packet.md": b"# Packet V8\n",
            "state.json": b'{"fractal_type":"explaino_all"}\n',
            "web-agent-frame.png": b"not-a-real-png-but-transport-bytes",
        }
        roles = {
            "packet.md": "agent_packet_index",
            "state.json": "engine_state_authority",
            "web-agent-frame.png": "web_discussion_derivative",
        }
        records = []
        for name, payload in self.payloads.items():
            (self.packet_dir / name).write_bytes(payload)
            records.append(
                {
                    "path": name,
                    "role": roles[name],
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "web_handoff": "required",
                }
            )
        self.order = ("packet.md", "manifest.json", "state.json", "web-agent-frame.png")
        self.manifest = {
            "packet_version": 8,
            "drag_all_attachments": list(self.order),
            "files": records,
        }
        self.manifest_bytes = _json_bytes(self.manifest)
        (self.packet_dir / "manifest.json").write_bytes(self.manifest_bytes)
        self.handoff = AgentBundleHandoff(
            packet_version=8,
            packet_dir=self.packet_dir,
            packet_text="# Packet V8\n",
            packet_sha256=hashlib.sha256(self.payloads["packet.md"]).hexdigest(),
            required_attachments=self.order,
            recommended_attachments=(),
            unavailable_optional_attachments=("field-notes.md",),
        )


class OpenAITransportTests(unittest.TestCase):
    def _store(self, root: Path) -> AutomatedRunStore:
        initialize_workspace_root(root)
        return AutomatedRunStore.create(
            root,
            run_id="transport-run",
            protocol_snapshot={"schema": "agent_session_protocol.v1"},
            initial_packet={"packet_id": "packet-v8"},
        )

    def test_prepare_is_manifest_ordered_role_bound_and_hash_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = PacketFixture(Path(temp_dir))
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ):
                prepared = prepare_packet_transport(fixture.packet_dir)
                self.assertEqual([item.filename for item in prepared.resources], list(fixture.order))
                self.assertEqual(prepared.resources[1].role, "packet_manifest")
                self.assertEqual(prepared.resources[-1].media_role, "vision")
                self.assertEqual(prepared.unavailable_optional_attachments, ("field-notes.md",))

                fixture.manifest["files"][1]["sha256"] = "0" * 64
                (fixture.packet_dir / "manifest.json").write_bytes(_json_bytes(fixture.manifest))
                with self.assertRaisesRegex(ValueError, "changed"):
                    prepare_packet_transport(fixture.packet_dir)

    def test_send_turn_uses_files_vision_continuation_and_cleans_owned_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = PacketFixture(root)
            provider = FakeProvider()
            store = self._store(root / "workspace")
            transport = PacketV8ResponsesTransport(provider)
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ):
                result = transport.send_turn(
                    instructions="Stable protocol instructions",
                    prompt="What do you notice?",
                    packet_dir=fixture.packet_dir,
                    previous_response_id="resp-previous",
                    run_store=store,
                    turn_id="turn-0002",
                )

            self.assertEqual(provider.uploaded, ["packet.md", "manifest.json", "state.json"])
            self.assertEqual(len(provider.count_requests), 1)
            self.assertEqual(provider.deleted, [])
            self.assertEqual(
                transport.owned_provider_file_ids,
                ("file-packet.md", "file-manifest.json", "file-state.json"),
            )
            request = provider.requests[0]["request"]
            self.assertEqual(request["model"], "gpt-5.6")
            self.assertEqual(request["reasoning"], {"effort": "high"})
            self.assertEqual(request["max_output_tokens"], 24_000)
            self.assertTrue(request["store"])
            self.assertEqual(request["previous_response_id"], "resp-previous")
            self.assertEqual(request["instructions"], "Stable protocol instructions")
            content = request["input"][0]["content"]
            self.assertEqual([item["type"] for item in content], [
                "input_text", "input_file", "input_file", "input_file", "input_image"
            ])
            self.assertTrue(content[-1]["image_url"].startswith("data:image/png;base64,"))
            self.assertEqual(result.input_tokens, 123)
            self.assertEqual(result.cached_input_tokens, 23)
            self.assertEqual(result.cache_write_tokens, 17)
            self.assertEqual(result.uncached_input_tokens, 100)
            self.assertEqual(result.output_tokens, 45)
            self.assertEqual(result.requested_model, "gpt-5.6")
            self.assertEqual(result.model, "gpt-5.6-2026-07-01")
            self.assertGreaterEqual(result.latency_seconds, 0.0)
            self.assertTrue(result.request_evidence_path.is_file())
            self.assertTrue(result.response_evidence_path.is_file())
            transport.close_owned_files(run_store=store)
            self.assertEqual(
                provider.deleted,
                ["file-state.json", "file-manifest.json", "file-packet.md"],
            )
            cleanup = json.loads(
                (store.run_dir / "transport/provider-file-cleanup.json").read_text(encoding="utf-8")
            )
            self.assertTrue(cleanup["cleanup_complete"])
            evidence = json.loads(result.request_evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [item["filename"] for item in evidence["resources"]],
                list(fixture.order),
            )
            self.assertIsNone(evidence["resources"][-1]["provider_file_id"])
            evidence_image = evidence["request"]["input"][0]["content"][-1]["image_url"]
            self.assertEqual(
                evidence_image,
                "[PACKET_IMAGE_DATA_URL_OMITTED; SEE RESOURCE SHA256]",
            )
            response_evidence = json.loads(
                result.response_evidence_path.read_text(encoding="utf-8")
            )
            self.assertEqual(response_evidence["requested_model"], "gpt-5.6")
            self.assertEqual(response_evidence["resolved_model"], "gpt-5.6-2026-07-01")
            self.assertEqual(response_evidence["cached_input_tokens"], 23)
            self.assertEqual(response_evidence["cache_write_tokens"], 17)
            self.assertEqual(response_evidence["uncached_input_tokens"], 100)

    def test_exact_token_count_gate_rejects_before_generation_and_cleans_uploads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = PacketFixture(root)
            provider = FakeProvider()
            transport = PacketV8ResponsesTransport(provider)
            with (
                patch(
                    "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                    return_value=fixture.handoff,
                ),
                self.assertRaisesRegex(DispatchAuthorizationRejected, "dollar gate"),
            ):
                transport.send_turn(
                    instructions="Stable protocol instructions",
                    prompt="What do you notice?",
                    packet_dir=fixture.packet_dir,
                    authorize_dispatch=lambda _count: (_ for _ in ()).throw(
                        DispatchAuthorizationRejected("dollar gate rejected")
                    ),
                )
            self.assertEqual(len(provider.count_requests), 1)
            self.assertEqual(provider.requests, [])
            self.assertEqual(
                provider.deleted,
                ["file-state.json", "file-manifest.json", "file-packet.md"],
            )
            self.assertEqual(transport.owned_provider_file_ids, ())

    def test_exact_role_and_hash_resources_reuse_one_owned_provider_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture = PacketFixture(root)
            provider = FakeProvider()
            transport = PacketV8ResponsesTransport(provider)
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ):
                first = transport.send_turn(
                    instructions="Stable protocol instructions",
                    prompt="First",
                    packet_dir=fixture.packet_dir,
                )
                second = transport.send_turn(
                    instructions="Stable protocol instructions",
                    prompt="Second fresh context",
                    packet_dir=fixture.packet_dir,
                )
            self.assertEqual(provider.uploaded, ["packet.md", "manifest.json", "state.json"])
            self.assertTrue(all(not item.provider_reused for item in first.resources))
            second_files = [item for item in second.resources if item.media_role == "file"]
            self.assertTrue(all(item.provider_reused for item in second_files))
            self.assertEqual(len(transport.owned_provider_file_ids), 3)
            transport.close_owned_files()
            self.assertEqual(len(provider.deleted), 3)

    def test_continuation_without_packet_sends_only_prompt_and_repeats_instructions(self) -> None:
        provider = FakeProvider()
        result = PacketV8ResponsesTransport(provider).send_turn(
            instructions="Stable instructions again",
            prompt="What would you try?",
            packet_dir=None,
            previous_response_id="resp-1",
        )
        request = provider.requests[0]["request"]
        self.assertEqual(request["instructions"], "Stable instructions again")
        self.assertEqual(request["previous_response_id"], "resp-1")
        self.assertEqual(request["input"], [{"role": "user", "content": [
            {"type": "input_text", "text": "What would you try?"}
        ]}])
        self.assertEqual(result.resources, ())

    def test_cancellation_before_dispatch_is_clean(self) -> None:
        provider = FakeProvider()
        with self.assertRaises(TransportCancelled):
            PacketV8ResponsesTransport(provider).send_turn(
                instructions="instructions",
                prompt="prompt",
                packet_dir=None,
                previous_response_id="resp-1",
                cancelled=lambda: True,
            )
        self.assertEqual(provider.requests, [])

    def test_cancellation_after_dispatch_preserves_durable_response_and_never_resends(self) -> None:
        provider = FakeProvider()
        cancelled = {"value": False}
        provider.on_response = lambda: cancelled.__setitem__("value", True)
        with self.assertRaises(AmbiguousRemoteCompletion) as captured:
            PacketV8ResponsesTransport(provider).send_turn(
                instructions="instructions",
                prompt="prompt",
                packet_dir=None,
                previous_response_id="resp-1",
                cancelled=lambda: cancelled["value"],
            )
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(captured.exception.durable_response.response_id, "resp-1")

    def test_ambiguous_provider_timeout_retains_owned_files_for_manual_disposition(self) -> None:
        class APITimeoutError(Exception):
            pass

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = PacketFixture(Path(temp_dir))
            provider = FakeProvider()
            provider.response_error = APITimeoutError("request timed out")
            transport = PacketV8ResponsesTransport(provider)
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ), self.assertRaises(ProviderTransportError) as captured:
                transport.send_turn(
                    instructions="instructions",
                    prompt="prompt",
                    packet_dir=fixture.packet_dir,
                )
            self.assertEqual(captured.exception.kind, ProviderFailureKind.TIMEOUT)
            self.assertTrue(captured.exception.remote_completion_ambiguous)
            self.assertEqual(provider.deleted, [])
            self.assertEqual(len(transport.owned_provider_file_ids), 3)
            transport.close_owned_files(reason="manual_disposition")
            self.assertEqual(len(transport.owned_provider_file_ids), 0)

    def test_definitive_provider_rejection_cleans_turn_uploads(self) -> None:
        class AuthenticationError(Exception):
            pass

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = PacketFixture(Path(temp_dir))
            provider = FakeProvider()
            provider.response_error = AuthenticationError("bad key")
            transport = PacketV8ResponsesTransport(provider)
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ), self.assertRaises(ProviderTransportError) as captured:
                transport.send_turn(
                    instructions="instructions",
                    prompt="prompt",
                    packet_dir=fixture.packet_dir,
                )
            self.assertEqual(captured.exception.kind, ProviderFailureKind.AUTHENTICATION)
            self.assertFalse(captured.exception.remote_completion_ambiguous)
            self.assertEqual(len(transport.owned_provider_file_ids), 0)
            self.assertEqual(len(provider.deleted), 3)

    def test_incomplete_response_is_not_accepted(self) -> None:
        provider = FakeProvider()
        provider.response_status = "incomplete"
        with self.assertRaises(ProviderTransportError) as captured:
            PacketV8ResponsesTransport(provider).send_turn(
                instructions="instructions",
                prompt="prompt",
                packet_dir=None,
                previous_response_id="resp-1",
            )
        self.assertEqual(captured.exception.kind, ProviderFailureKind.MALFORMED_RESPONSE)

    def test_failure_classifier_separates_control_and_ambiguous_failures(self) -> None:
        cases = [
            (type("AuthenticationError", (Exception,), {})("bad key"), ProviderFailureKind.AUTHENTICATION, False),
            (type("RateLimitError", (Exception,), {})("limited"), ProviderFailureKind.RATE_LIMIT, False),
            (type("InternalServerError", (Exception,), {"status_code": 500})("server"), ProviderFailureKind.SERVER, True),
            (ValueError("content_policy violation"), ProviderFailureKind.CONTENT_POLICY, False),
        ]
        for error, kind, ambiguous in cases:
            with self.subTest(kind=kind):
                classified = classify_provider_failure(error, dispatched=True)
                self.assertEqual(classified.kind, kind)
                self.assertEqual(classified.remote_completion_ambiguous, ambiguous)

    def test_cleanup_failure_is_not_reported_as_success(self) -> None:
        class CleanupFailingProvider(FakeProvider):
            def delete_file(self, file_id: str) -> None:
                super().delete_file(file_id)
                raise RuntimeError("delete failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = PacketFixture(Path(temp_dir))
            provider = CleanupFailingProvider()
            transport = PacketV8ResponsesTransport(provider)
            with patch(
                "cuda_fractal_state_tool.openai_transport.load_agent_bundle_handoff",
                return_value=fixture.handoff,
            ), self.assertRaises(ProviderTransportError) as captured:
                transport.send_turn(
                    instructions="instructions",
                    prompt="prompt",
                    packet_dir=fixture.packet_dir,
                )
                transport.close_owned_files()
            self.assertEqual(captured.exception.kind, ProviderFailureKind.FILE_CLEANUP)

    def test_sanitizer_removes_secrets_but_keeps_token_usage(self) -> None:
        sanitized = sanitize_evidence(
            {
                "api_key": "sk-secret",
                "Authorization": "Bearer sk-secret",
                "nested": {"client_secret": "secret", "input_tokens": 42},
                "message": "Bearer another-secret",
            }
        )
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertEqual(sanitized["Authorization"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["client_secret"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["input_tokens"], 42)
        self.assertEqual(sanitized["message"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
