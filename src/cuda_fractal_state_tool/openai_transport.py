from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import time
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

from .agent_bundle import AgentBundleHandoff, load_agent_bundle_handoff
from .automated_run_store import AutomatedRunStore
from .json_utils import loads_strict_no_duplicates


DEFAULT_MODEL = "gpt-5.6"
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_MAX_OUTPUT_TOKENS = 24_000
DEFAULT_RESPONSE_TIMEOUT_SECONDS = 600.0


class ProviderFailureKind(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    RATE_LIMIT = "RATE_LIMIT"
    CONTENT_POLICY = "CONTENT_POLICY"
    INVALID_REQUEST = "INVALID_REQUEST"
    TIMEOUT = "TIMEOUT"
    CONNECTION = "CONNECTION"
    SERVER = "SERVER"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    UNKNOWN = "UNKNOWN"
    FILE_CLEANUP = "FILE_CLEANUP"


class TransportCancelled(RuntimeError):
    pass


class DispatchAuthorizationRejected(RuntimeError):
    pass


class ProviderTransportError(RuntimeError):
    def __init__(
        self,
        kind: ProviderFailureKind,
        message: str,
        *,
        remote_completion_ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.remote_completion_ambiguous = remote_completion_ambiguous


class AmbiguousRemoteCompletion(RuntimeError):
    def __init__(self, message: str, *, durable_response: "TransportTurnResult | None" = None) -> None:
        super().__init__(message)
        self.durable_response = durable_response


@dataclass(frozen=True)
class ProviderFile:
    id: str
    filename: str


@dataclass(frozen=True)
class ProviderResponse:
    id: str
    model: str
    status: str
    output_text: str
    usage: dict[str, int]
    raw: dict[str, Any]


class ResponsesProvider(Protocol):
    def upload_file(self, filename: str, payload: bytes) -> ProviderFile: ...

    def create_response(self, request: dict[str, Any], *, timeout_seconds: float) -> ProviderResponse: ...

    def count_input_tokens(self, request: dict[str, Any], *, timeout_seconds: float) -> int: ...

    def delete_file(self, file_id: str) -> None: ...


@dataclass(frozen=True)
class TransportResource:
    filename: str
    role: str
    media_role: str
    sha256: str
    size_bytes: int
    local_path: Path
    payload: bytes
    provider_file_id: str | None = None
    provider_reused: bool = False

    def to_evidence(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "role": self.role,
            "media_role": self.media_role,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "provider_file_id": self.provider_file_id,
            "provider_reused": self.provider_reused,
        }


@dataclass(frozen=True)
class PreparedPacketTransport:
    handoff: AgentBundleHandoff
    manifest_sha256: str
    resources: tuple[TransportResource, ...]
    unavailable_optional_attachments: tuple[str, ...]


@dataclass(frozen=True)
class TransportTurnResult:
    response_id: str
    previous_response_id: str | None
    model: str
    output_text: str
    input_tokens: int
    output_tokens: int
    resources: tuple[TransportResource, ...]
    unavailable_optional_attachments: tuple[str, ...]
    requested_model: str = ""
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    latency_seconds: float = 0.0
    request_evidence_path: Path | None = None
    response_evidence_path: Path | None = None

    @property
    def uncached_input_tokens(self) -> int:
        return self.input_tokens - self.cached_input_tokens


class OpenAISDKProvider:
    """Thin, retry-free SDK adapter. Conversation retry authority stays in the controller."""

    def __init__(self, api_key: str) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key is required")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise RuntimeError("The openai package is required for automated sessions") from exc
        self._client = OpenAI(api_key=api_key, max_retries=0)

    def upload_file(self, filename: str, payload: bytes) -> ProviderFile:
        value = self._client.files.create(file=(filename, payload), purpose="user_data")
        return ProviderFile(id=value.id, filename=value.filename)

    def create_response(self, request: dict[str, Any], *, timeout_seconds: float) -> ProviderResponse:
        value = self._client.responses.create(**request, timeout=timeout_seconds)
        raw = value.model_dump(mode="json")
        usage_raw = raw.get("usage") or {}
        input_details = usage_raw.get("input_tokens_details") or {}
        usage = {
            "input_tokens": int(usage_raw.get("input_tokens") or 0),
            "cached_input_tokens": int(input_details.get("cached_tokens") or 0),
            "cache_write_tokens": int(input_details.get("cache_write_tokens") or 0),
            "output_tokens": int(usage_raw.get("output_tokens") or 0),
        }
        return ProviderResponse(
            id=value.id,
            model=value.model,
            status=value.status,
            output_text=value.output_text,
            usage=usage,
            raw=raw,
        )

    def count_input_tokens(self, request: dict[str, Any], *, timeout_seconds: float) -> int:
        count_request = {
            key: request[key]
            for key in ("model", "instructions", "input", "previous_response_id")
            if key in request
        }
        value = self._client.responses.input_tokens.count(
            **count_request,
            timeout=timeout_seconds,
        )
        count = int(value.input_tokens)
        if count < 0:
            raise ValueError("Provider returned a negative input-token count")
        return count

    def delete_file(self, file_id: str) -> None:
        self._client.files.delete(file_id)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_manifest(packet_dir: Path) -> tuple[dict[str, Any], bytes]:
    payload = (packet_dir / "manifest.json").read_bytes()
    try:
        value = loads_strict_no_duplicates(payload.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Packet manifest is malformed or contains duplicate keys") from exc
    if not isinstance(value, dict):
        raise ValueError("Packet manifest must be a JSON object")
    return value, payload


def prepare_packet_transport(packet_dir: Path) -> PreparedPacketTransport:
    handoff = load_agent_bundle_handoff(packet_dir)
    if handoff.packet_version != 8:
        raise ValueError("Automated transport requires Packet V8")
    manifest, manifest_bytes = _load_manifest(handoff.packet_dir)
    drag_all = manifest.get("drag_all_attachments")
    if not isinstance(drag_all, list) or drag_all != list(handoff.required_attachments):
        raise ValueError("Packet V8 transport order disagrees with validated handoff")
    records_raw = manifest.get("files")
    if not isinstance(records_raw, list):
        raise ValueError("Packet V8 manifest has no file records")
    records = {
        item.get("path"): item
        for item in records_raw
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    if len(records) != len(records_raw):
        raise ValueError("Packet V8 manifest file records are invalid or duplicated")

    resources: list[TransportResource] = []
    for filename in drag_all:
        path = handoff.packet_dir / filename
        payload = path.read_bytes()
        if filename == "manifest.json":
            role = "packet_manifest"
            expected_sha = _sha256(manifest_bytes)
            expected_size = len(manifest_bytes)
        else:
            record = records.get(filename)
            if record is None:
                raise ValueError(f"Packet V8 transport resource has no file record: {filename}")
            role = record.get("role")
            expected_sha = record.get("sha256")
            expected_size = record.get("size_bytes")
            if not isinstance(role, str) or not role:
                raise ValueError(f"Packet V8 transport resource has no role: {filename}")
        if _sha256(payload) != expected_sha or len(payload) != expected_size:
            raise ValueError(f"Packet V8 transport resource changed: {filename}")
        media_role = "vision" if role == "web_discussion_derivative" else "file"
        resources.append(
            TransportResource(
                filename=filename,
                role=role,
                media_role=media_role,
                sha256=expected_sha,
                size_bytes=expected_size,
                local_path=path,
                payload=payload,
            )
        )
    return PreparedPacketTransport(
        handoff=handoff,
        manifest_sha256=_sha256(manifest_bytes),
        resources=tuple(resources),
        unavailable_optional_attachments=handoff.unavailable_optional_attachments,
    )


def sanitize_evidence(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"api_key", "authorization", "credential", "secret"} or lowered.endswith(
                ("_api_key", "_secret")
            ):
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = sanitize_evidence(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_evidence(item) for item in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "[REDACTED]"
    if isinstance(value, str) and value.lower().startswith("data:image/"):
        return "[PACKET_IMAGE_DATA_URL_OMITTED; SEE RESOURCE SHA256]"
    return value


def classify_provider_failure(exc: Exception, *, dispatched: bool) -> ProviderTransportError:
    name = exc.__class__.__name__
    status = getattr(exc, "status_code", None)
    message = str(exc) or name
    lowered = message.lower()
    if name == "AuthenticationError" or status == 401:
        kind = ProviderFailureKind.AUTHENTICATION
    elif name == "PermissionDeniedError" or status == 403:
        kind = ProviderFailureKind.PERMISSION
    elif name == "RateLimitError" or status == 429:
        kind = ProviderFailureKind.RATE_LIMIT
    elif "content_policy" in lowered or "content policy" in lowered:
        kind = ProviderFailureKind.CONTENT_POLICY
    elif name == "APITimeoutError" or "timeout" in name.lower():
        kind = ProviderFailureKind.TIMEOUT
    elif name == "APIConnectionError" or "connection" in name.lower():
        kind = ProviderFailureKind.CONNECTION
    elif isinstance(status, int) and status >= 500:
        kind = ProviderFailureKind.SERVER
    elif name in {"BadRequestError", "UnprocessableEntityError", "NotFoundError"} or status in {
        400,
        404,
        422,
    }:
        kind = ProviderFailureKind.INVALID_REQUEST
    else:
        kind = ProviderFailureKind.UNKNOWN
    ambiguous = dispatched and kind in {
        ProviderFailureKind.TIMEOUT,
        ProviderFailureKind.CONNECTION,
        ProviderFailureKind.SERVER,
        ProviderFailureKind.UNKNOWN,
    }
    return ProviderTransportError(kind, message, remote_completion_ambiguous=ambiguous)


def _image_data_url(resource: TransportResource) -> str:
    media_type = mimetypes.guess_type(resource.filename)[0] or "image/png"
    encoded = base64.b64encode(resource.payload).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


class PacketV8ResponsesTransport:
    def __init__(self, provider: ResponsesProvider) -> None:
        self.provider = provider
        self._owned_provider_file_ids: list[str] = []
        self._provider_file_by_identity: dict[tuple[str, str], str] = {}

    @property
    def owned_provider_file_ids(self) -> tuple[str, ...]:
        return tuple(self._owned_provider_file_ids)

    def restore_owned_provider_files(self, file_ids: list[str] | tuple[str, ...]) -> None:
        if self._owned_provider_file_ids:
            raise ValueError("Cannot restore provider-file ownership over an active transport")
        if any(not isinstance(item, str) or not item for item in file_ids):
            raise ValueError("Provider-file ownership contains an invalid identity")
        if len(file_ids) != len(set(file_ids)):
            raise ValueError("Provider-file ownership contains duplicate identities")
        self._owned_provider_file_ids.extend(file_ids)

    def close_owned_files(
        self,
        *,
        run_store: AutomatedRunStore | None = None,
        reason: str = "session_closed",
    ) -> None:
        failures = self._cleanup_file_ids(tuple(self._owned_provider_file_ids))
        if run_store is not None:
            run_store.write_evidence_json(
                "transport/provider-file-cleanup.json",
                {
                    "reason": reason,
                    "cleanup_complete": not failures,
                    "remaining_provider_file_ids": list(self._owned_provider_file_ids),
                    "failures": failures,
                },
            )
        if failures:
            raise ProviderTransportError(
                ProviderFailureKind.FILE_CLEANUP,
                "Owned provider-file cleanup failed: " + "; ".join(failures),
            )

    def _record_owned_files(self, run_store: AutomatedRunStore | None) -> None:
        if run_store is not None:
            run_store.write_evidence_json(
                "transport/owned-provider-files.json",
                {
                    "provider_file_ids": list(self._owned_provider_file_ids),
                    "cleanup_required": bool(self._owned_provider_file_ids),
                },
            )

    def _cleanup_file_ids(self, file_ids: tuple[str, ...]) -> list[str]:
        failures: list[str] = []
        for file_id in reversed(file_ids):
            try:
                self.provider.delete_file(file_id)
            except Exception as exc:
                failures.append(f"{file_id}: {exc}")
            else:
                if file_id in self._owned_provider_file_ids:
                    self._owned_provider_file_ids.remove(file_id)
                self._provider_file_by_identity = {
                    identity: owned_id
                    for identity, owned_id in self._provider_file_by_identity.items()
                    if owned_id != file_id
                }
        return failures

    def send_turn(
        self,
        *,
        instructions: str,
        prompt: str,
        packet_dir: Path | None,
        previous_response_id: str | None = None,
        run_store: AutomatedRunStore | None = None,
        turn_id: str = "turn-0001",
        cancelled: Callable[[], bool] = lambda: False,
        model: str = DEFAULT_MODEL,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        timeout_seconds: float = DEFAULT_RESPONSE_TIMEOUT_SECONDS,
        authorize_dispatch: Callable[[int], None] | None = None,
        additional_resources: tuple[TransportResource, ...] = (),
    ) -> TransportTurnResult:
        if not instructions.strip() or not prompt.strip():
            raise ValueError("Automated response instructions and prompt are required")
        if packet_dir is None and previous_response_id is None:
            raise ValueError("The first automated turn requires a Packet V8 authority bundle")
        if cancelled():
            raise TransportCancelled("Automated turn was cancelled before API dispatch")
        prepared = prepare_packet_transport(packet_dir) if packet_dir is not None else None
        resources = list(prepared.resources if prepared else ())
        for resource in additional_resources:
            if not isinstance(resource, TransportResource):
                raise ValueError("Additional transport resources must be exact TransportResource values")
            current = resource.local_path.read_bytes()
            if (
                current != resource.payload
                or _sha256(current) != resource.sha256
                or len(current) != resource.size_bytes
            ):
                raise ValueError(f"Additional transport resource changed: {resource.filename}")
            resources.append(resource)
        by_filename: dict[str, tuple[str, str, str]] = {}
        deduplicated: list[TransportResource] = []
        seen_identities: set[tuple[str, str, str]] = set()
        for resource in resources:
            identity = (resource.role, resource.sha256, resource.media_role)
            prior = by_filename.get(resource.filename)
            if prior is not None and prior != identity:
                raise ValueError(f"Transport filename identifies different resources: {resource.filename}")
            by_filename[resource.filename] = identity
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            deduplicated.append(resource)
        resources = deduplicated
        turn_uploaded_ids: list[str] = []
        request_content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        dispatched = False
        request_evidence_path: Path | None = None
        response_evidence_path: Path | None = None
        try:
            for index, resource in enumerate(resources):
                if cancelled():
                    raise TransportCancelled("Automated turn was cancelled before API dispatch")
                if resource.media_role == "vision":
                    request_content.append(
                        {"type": "input_image", "detail": "high", "image_url": _image_data_url(resource)}
                    )
                    continue
                provider_identity = (resource.role, resource.sha256)
                reused_file_id = self._provider_file_by_identity.get(provider_identity)
                if reused_file_id is not None:
                    resources[index] = replace(
                        resource,
                        provider_file_id=reused_file_id,
                        provider_reused=True,
                    )
                    request_content.append({"type": "input_file", "file_id": reused_file_id})
                    continue
                provider_file = self.provider.upload_file(resource.filename, resource.payload)
                if not provider_file.id:
                    raise ValueError("Provider returned an invalid uploaded-file identity")
                turn_uploaded_ids.append(provider_file.id)
                self._owned_provider_file_ids.append(provider_file.id)
                self._provider_file_by_identity[provider_identity] = provider_file.id
                self._record_owned_files(run_store)
                resources[index] = replace(resource, provider_file_id=provider_file.id)
                request_content.append({"type": "input_file", "file_id": provider_file.id})
            if cancelled():
                raise TransportCancelled("Automated turn was cancelled before API dispatch")

            request: dict[str, Any] = {
                "model": model,
                "reasoning": {"effort": reasoning_effort},
                "max_output_tokens": max_output_tokens,
                "store": True,
                "instructions": instructions,
                "input": [{"role": "user", "content": request_content}],
            }
            if previous_response_id is not None:
                request["previous_response_id"] = previous_response_id
            request_evidence = {
                "request": request,
                "packet_manifest_sha256": prepared.manifest_sha256 if prepared else None,
                "resources": [resource.to_evidence() for resource in resources],
                "unavailable_optional_attachments": list(
                    prepared.unavailable_optional_attachments if prepared else ()
                ),
            }
            if run_store is not None:
                request_evidence_path = run_store.write_evidence_json(
                    f"transport/{turn_id}/request.json", sanitize_evidence(request_evidence)
                )
            try:
                counted_input_tokens = self.provider.count_input_tokens(
                    request,
                    timeout_seconds=timeout_seconds,
                )
            except Exception as exc:
                raise classify_provider_failure(exc, dispatched=False) from exc
            if counted_input_tokens < 0:
                raise ProviderTransportError(
                    ProviderFailureKind.MALFORMED_RESPONSE,
                    "Provider returned an invalid input-token count",
                )
            if run_store is not None:
                run_store.write_evidence_json(
                    f"transport/{turn_id}/input-token-count.json",
                    {
                        "input_tokens": counted_input_tokens,
                        "phase": "before_generation_dispatch",
                    },
                )
            if authorize_dispatch is not None:
                authorize_dispatch(counted_input_tokens)
            if cancelled():
                raise TransportCancelled("Automated turn was cancelled before API dispatch")
            dispatched = True
            started_at = time.monotonic()
            try:
                response = self.provider.create_response(request, timeout_seconds=timeout_seconds)
            except Exception as exc:
                raise classify_provider_failure(exc, dispatched=True) from exc
            latency_seconds = time.monotonic() - started_at
            if response.status != "completed":
                raise ProviderTransportError(
                    ProviderFailureKind.CONTENT_POLICY
                    if "content_policy" in json.dumps(response.raw).lower()
                    else ProviderFailureKind.MALFORMED_RESPONSE,
                    f"Provider response did not complete: {response.status}",
                )
            if (
                not response.id
                or not response.model
                or not isinstance(response.output_text, str)
                or not response.output_text.strip()
            ):
                raise ProviderTransportError(
                    ProviderFailureKind.MALFORMED_RESPONSE,
                    "Provider response is missing an identity, model, or output text",
                )
            input_tokens = int(response.usage.get("input_tokens", 0))
            cached_input_tokens = int(response.usage.get("cached_input_tokens", 0))
            cache_write_tokens = int(response.usage.get("cache_write_tokens", 0))
            output_tokens = int(response.usage.get("output_tokens", 0))
            if (
                input_tokens < 0
                or cached_input_tokens < 0
                or cached_input_tokens > input_tokens
                or cache_write_tokens < 0
                or cached_input_tokens + cache_write_tokens > input_tokens
                or output_tokens < 0
            ):
                raise ProviderTransportError(
                    ProviderFailureKind.MALFORMED_RESPONSE,
                    "Provider response contains invalid token usage",
                )
            result = TransportTurnResult(
                response_id=response.id,
                previous_response_id=previous_response_id,
                model=response.model,
                output_text=response.output_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                resources=tuple(resources),
                unavailable_optional_attachments=(
                    prepared.unavailable_optional_attachments if prepared else ()
                ),
                requested_model=model,
                cached_input_tokens=cached_input_tokens,
                cache_write_tokens=cache_write_tokens,
                latency_seconds=latency_seconds,
                request_evidence_path=request_evidence_path,
            )
            if run_store is not None:
                response_evidence_path = run_store.write_evidence_json(
                    f"transport/{turn_id}/response.json",
                    sanitize_evidence(
                        {
                            "response": response.raw,
                            "response_id": result.response_id,
                            "requested_model": result.requested_model,
                            "resolved_model": result.model,
                            "input_tokens": result.input_tokens,
                            "cached_input_tokens": result.cached_input_tokens,
                            "cache_write_tokens": result.cache_write_tokens,
                            "uncached_input_tokens": result.uncached_input_tokens,
                            "output_tokens": result.output_tokens,
                            "latency_seconds": result.latency_seconds,
                        }
                    ),
                )
                result = replace(result, response_evidence_path=response_evidence_path)
            if cancelled():
                raise AmbiguousRemoteCompletion(
                    "Local cancellation occurred after API dispatch; the captured response will not advance automatically",
                    durable_response=result,
                )
            return result
        except TransportCancelled:
            failures = self._cleanup_file_ids(tuple(turn_uploaded_ids))
            self._record_owned_files(run_store)
            if failures:
                raise ProviderTransportError(
                    ProviderFailureKind.FILE_CLEANUP,
                    "Pre-dispatch cancellation cleanup failed: " + "; ".join(failures),
                )
            raise
        except DispatchAuthorizationRejected:
            failures = self._cleanup_file_ids(tuple(turn_uploaded_ids))
            self._record_owned_files(run_store)
            if failures:
                raise ProviderTransportError(
                    ProviderFailureKind.FILE_CLEANUP,
                    "Rejected-dispatch cleanup failed: " + "; ".join(failures),
                )
            raise
        except ProviderTransportError as exc:
            if not exc.remote_completion_ambiguous:
                failures = self._cleanup_file_ids(tuple(turn_uploaded_ids))
                self._record_owned_files(run_store)
                if failures:
                    exc.add_note("Owned provider-file cleanup also failed: " + "; ".join(failures))
            raise
        except AmbiguousRemoteCompletion:
            self._record_owned_files(run_store)
            raise
        except Exception as exc:
            classified = classify_provider_failure(exc, dispatched=dispatched)
            if not classified.remote_completion_ambiguous:
                failures = self._cleanup_file_ids(tuple(turn_uploaded_ids))
                self._record_owned_files(run_store)
                if failures:
                    classified.add_note(
                        "Owned provider-file cleanup also failed: " + "; ".join(failures)
                    )
            raise classified from exc
