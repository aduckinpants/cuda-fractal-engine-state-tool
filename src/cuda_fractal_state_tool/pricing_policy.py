from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .json_utils import loads_strict_no_duplicates


PRICING_POLICY_SCHEMA = "openai_pricing_policy.v1"
DEFAULT_PRICING_POLICY_PATH = Path(__file__).with_name("openai_pricing_policy.v1.json")
PROVIDER_BILLING_DISCLAIMER = (
    "Calculated cost is a local usage-derived estimate; provider billing remains authoritative."
)


def _decimal(value: Any, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} is not a valid decimal") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return result


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class TokenRates:
    input: Decimal
    cached_input: Decimal
    cache_write: Decimal
    output: Decimal

    @classmethod
    def parse(cls, value: Any, label: str) -> "TokenRates":
        if not isinstance(value, dict) or set(value) != {
            "input",
            "cached_input",
            "cache_write",
            "output",
        }:
            raise ValueError(f"{label} must contain the four exact rate fields")
        return cls(**{key: _decimal(item, f"{label}.{key}") for key, item in value.items()})

    def to_dict(self) -> dict[str, str]:
        return {
            "input": decimal_text(self.input),
            "cached_input": decimal_text(self.cached_input),
            "cache_write": decimal_text(self.cache_write),
            "output": decimal_text(self.output),
        }


@dataclass(frozen=True)
class ModelPricing:
    pricing_model: str
    aliases: tuple[str, ...]
    short_context: TokenRates
    long_context: TokenRates


@dataclass(frozen=True)
class PricingPolicy:
    path: Path
    sha256: str
    policy_id: str
    effective_date: str
    currency: str
    tokens_per_rate_unit: int
    long_context_threshold_tokens: int
    source_url: str
    service_tier: str
    models: tuple[ModelPricing, ...]

    def model(self, model_name: str) -> ModelPricing:
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("A provider model identity is required for pricing")
        matches: list[tuple[int, ModelPricing]] = []
        for model in self.models:
            for alias in model.aliases:
                if model_name == alias or model_name.startswith(alias + "-"):
                    matches.append((len(alias), model))
        if not matches:
            raise ValueError(f"Pricing policy has no model match for: {model_name}")
        longest = max(length for length, _model in matches)
        owners = {model.pricing_model: model for length, model in matches if length == longest}
        if len(owners) != 1:
            raise ValueError(f"Pricing policy model match is ambiguous for: {model_name}")
        return next(iter(owners.values()))

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema": PRICING_POLICY_SCHEMA,
            "policy_id": self.policy_id,
            "effective_date": self.effective_date,
            "sha256": self.sha256,
            "source_url": self.source_url,
            "service_tier": self.service_tier,
            "currency": self.currency,
            "long_context_threshold_tokens": self.long_context_threshold_tokens,
        }


@dataclass(frozen=True)
class CallCost:
    pricing_model: str
    context_tier: str
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    ordinary_input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    conservative: bool
    assumption: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_model": self.pricing_model,
            "context_tier": self.context_tier,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "ordinary_input_tokens": self.ordinary_input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": decimal_text(self.cost_usd),
            "conservative": self.conservative,
            "assumption": self.assumption,
        }


def load_pricing_policy(path: Path | None = None) -> PricingPolicy:
    if path is None:
        configured = os.environ.get("CUDA_FRACTAL_OPENAI_PRICING_POLICY", "").strip()
        path = Path(configured) if configured else DEFAULT_PRICING_POLICY_PATH
    path = path.resolve()
    payload = path.read_bytes()
    try:
        value = loads_strict_no_duplicates(payload.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError(f"Pricing policy is malformed: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != PRICING_POLICY_SCHEMA:
        raise ValueError("Unsupported pricing-policy schema")
    required = {
        "schema",
        "policy_id",
        "effective_date",
        "currency",
        "tokens_per_rate_unit",
        "long_context_threshold_tokens",
        "source_url",
        "service_tier",
        "models",
    }
    if set(value) != required:
        raise ValueError("Pricing policy fields do not match the V1 contract")
    if value["currency"] != "USD" or value["service_tier"] != "standard":
        raise ValueError("V1 pricing gate supports standard USD pricing only")
    if not isinstance(value["tokens_per_rate_unit"], int) or value["tokens_per_rate_unit"] < 1:
        raise ValueError("Pricing policy has an invalid token rate unit")
    if (
        not isinstance(value["long_context_threshold_tokens"], int)
        or value["long_context_threshold_tokens"] < 1
    ):
        raise ValueError("Pricing policy has an invalid long-context threshold")
    models_raw = value["models"]
    if not isinstance(models_raw, list) or not models_raw:
        raise ValueError("Pricing policy must contain models")
    models: list[ModelPricing] = []
    aliases: set[str] = set()
    names: set[str] = set()
    for index, item in enumerate(models_raw):
        if not isinstance(item, dict) or set(item) != {
            "pricing_model",
            "aliases",
            "short_context",
            "long_context",
        }:
            raise ValueError(f"Pricing model {index} has invalid fields")
        name = item["pricing_model"]
        model_aliases = item["aliases"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("Pricing model identities must be unique non-empty strings")
        if (
            not isinstance(model_aliases, list)
            or not model_aliases
            or any(not isinstance(alias, str) or not alias for alias in model_aliases)
            or len(model_aliases) != len(set(model_aliases))
        ):
            raise ValueError(f"Pricing aliases are invalid for {name}")
        overlap = aliases.intersection(model_aliases)
        if overlap:
            raise ValueError(f"Pricing aliases are duplicated: {sorted(overlap)}")
        names.add(name)
        aliases.update(model_aliases)
        models.append(
            ModelPricing(
                pricing_model=name,
                aliases=tuple(model_aliases),
                short_context=TokenRates.parse(item["short_context"], f"{name}.short_context"),
                long_context=TokenRates.parse(item["long_context"], f"{name}.long_context"),
            )
        )
    for field in ("policy_id", "effective_date", "source_url"):
        if not isinstance(value[field], str) or not value[field]:
            raise ValueError(f"Pricing policy {field} is required")
    return PricingPolicy(
        path=path,
        sha256=hashlib.sha256(payload).hexdigest(),
        policy_id=value["policy_id"],
        effective_date=value["effective_date"],
        currency=value["currency"],
        tokens_per_rate_unit=value["tokens_per_rate_unit"],
        long_context_threshold_tokens=value["long_context_threshold_tokens"],
        source_url=value["source_url"],
        service_tier=value["service_tier"],
        models=tuple(models),
    )


def estimate_maximum_call_cost(
    policy: PricingPolicy,
    *,
    model_name: str,
    maximum_input_tokens: int,
    maximum_output_tokens: int,
    prompt_cache_policy: str = "implicit",
) -> CallCost:
    if maximum_input_tokens < 0 or maximum_output_tokens < 0:
        raise ValueError("Maximum token estimates cannot be negative")
    model = policy.model(model_name)
    long_context = maximum_input_tokens >= policy.long_context_threshold_tokens
    rates = model.long_context if long_context else model.short_context
    if prompt_cache_policy == "explicit_no_cache":
        conservative_input_rate = rates.input
        cached_input_tokens = 0
        cache_write_tokens = 0
        ordinary_input_tokens = maximum_input_tokens
        assumption = (
            "Prompt caching is explicitly disabled; all bounded input is priced at the "
            "ordinary input rate."
        )
    elif prompt_cache_policy == "implicit":
        conservative_input_rate = max(rates.input, rates.cached_input, rates.cache_write)
        cached_input_tokens = 0
        cache_write_tokens = maximum_input_tokens
        ordinary_input_tokens = 0
        assumption = "All bounded input is priced at the maximum applicable input-side rate."
    else:
        raise ValueError(f"Unsupported prompt-cache policy: {prompt_cache_policy}")
    cost = (
        Decimal(maximum_input_tokens) * conservative_input_rate
        + Decimal(maximum_output_tokens) * rates.output
    ) / Decimal(policy.tokens_per_rate_unit)
    return CallCost(
        pricing_model=model.pricing_model,
        context_tier="long" if long_context else "short",
        input_tokens=maximum_input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        ordinary_input_tokens=ordinary_input_tokens,
        output_tokens=maximum_output_tokens,
        cost_usd=cost,
        conservative=True,
        assumption=assumption,
    )


def calculate_usage_cost(
    policy: PricingPolicy,
    *,
    model_name: str,
    input_tokens: int,
    cached_input_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
) -> CallCost:
    if any(value < 0 for value in (input_tokens, cached_input_tokens, cache_write_tokens, output_tokens)):
        raise ValueError("Provider token usage cannot be negative")
    if cached_input_tokens + cache_write_tokens > input_tokens:
        raise ValueError("Cache reads and writes cannot exceed total input tokens")
    ordinary_input = input_tokens - cached_input_tokens - cache_write_tokens
    model = policy.model(model_name)
    long_context = input_tokens >= policy.long_context_threshold_tokens
    rates = model.long_context if long_context else model.short_context
    cost = (
        Decimal(ordinary_input) * rates.input
        + Decimal(cached_input_tokens) * rates.cached_input
        + Decimal(cache_write_tokens) * rates.cache_write
        + Decimal(output_tokens) * rates.output
    ) / Decimal(policy.tokens_per_rate_unit)
    return CallCost(
        pricing_model=model.pricing_model,
        context_tier="long" if long_context else "short",
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        cache_write_tokens=cache_write_tokens,
        ordinary_input_tokens=ordinary_input,
        output_tokens=output_tokens,
        cost_usd=cost,
        conservative=False,
        assumption=PROVIDER_BILLING_DISCLAIMER,
    )
