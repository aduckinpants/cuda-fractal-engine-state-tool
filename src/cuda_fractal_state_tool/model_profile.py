from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .openai_transport import (
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    PromptCachePolicy,
)
from .pricing_policy import PricingPolicy


MODEL_PROFILE_VERSION = 1
SUPPORTED_REASONING_EFFORTS = frozenset({"medium", "high"})


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


@dataclass(frozen=True)
class ModelProfileV1:
    model: str = DEFAULT_MODEL
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    pricing_tier: str = "standard"
    prompt_cache_policy: PromptCachePolicy = PromptCachePolicy.EXPLICIT_NO_CACHE

    def validate(self, policy: PricingPolicy) -> None:
        policy.model(self.model)
        if self.reasoning_effort not in SUPPORTED_REASONING_EFFORTS:
            raise ValueError(
                "Model-profile reasoning effort must be one of: "
                + ", ".join(sorted(SUPPORTED_REASONING_EFFORTS))
            )
        if self.pricing_tier != policy.service_tier or self.pricing_tier != "standard":
            raise ValueError("Model Profile V1 supports only the tracked standard pricing tier")
        if PromptCachePolicy(self.prompt_cache_policy) is not PromptCachePolicy.EXPLICIT_NO_CACHE:
            raise ValueError("Qualification profiles require explicit no-cache transport")

    def to_dict(self) -> dict[str, str | int]:
        return {
            "profile_version": MODEL_PROFILE_VERSION,
            "model": self.model,
            "reasoning_effort": self.reasoning_effort,
            "pricing_tier": self.pricing_tier,
            "prompt_cache_policy": PromptCachePolicy(self.prompt_cache_policy).value,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.to_dict())).hexdigest()

    def identity_dict(self) -> dict[str, Any]:
        return {**self.to_dict(), "sha256": self.sha256}
