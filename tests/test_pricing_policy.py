from __future__ import annotations

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.pricing_policy import (
    calculate_usage_cost,
    estimate_maximum_call_cost,
    load_pricing_policy,
)


class PricingPolicyTests(unittest.TestCase):
    def test_default_policy_matches_locked_standard_sol_rates(self) -> None:
        policy = load_pricing_policy()
        self.assertEqual(policy.policy_id, "openai-standard-2026-08-03")
        self.assertEqual(policy.long_context_threshold_tokens, 272_000)
        sol = policy.model("gpt-5.6-2026-07-01")
        self.assertEqual(sol.pricing_model, "gpt-5.6-sol")
        self.assertEqual(sol.short_context.cache_write, Decimal("6.25"))
        self.assertEqual(policy.model("gpt-5.6-terra-2026-07-01").pricing_model, "gpt-5.6-terra")

    def test_conservative_estimate_uses_highest_input_side_rate_and_context_tier(self) -> None:
        policy = load_pricing_policy()
        short = estimate_maximum_call_cost(
            policy,
            model_name="gpt-5.6",
            maximum_input_tokens=200_000,
            maximum_output_tokens=24_000,
        )
        self.assertEqual(short.context_tier, "short")
        self.assertEqual(short.cost_usd, Decimal("1.97"))
        long = estimate_maximum_call_cost(
            policy,
            model_name="gpt-5.6",
            maximum_input_tokens=272_000,
            maximum_output_tokens=24_000,
        )
        self.assertEqual(long.context_tier, "long")
        self.assertEqual(long.cost_usd, Decimal("4.48"))

    def test_explicit_no_cache_estimate_uses_ordinary_input_rate(self) -> None:
        cost = estimate_maximum_call_cost(
            load_pricing_policy(),
            model_name="gpt-5.6",
            maximum_input_tokens=200_000,
            maximum_output_tokens=8_000,
            prompt_cache_policy="explicit_no_cache",
        )
        self.assertEqual(cost.context_tier, "short")
        self.assertEqual(cost.ordinary_input_tokens, 200_000)
        self.assertEqual(cost.cache_write_tokens, 0)
        self.assertEqual(cost.cost_usd, Decimal("1.24"))

        with self.assertRaisesRegex(ValueError, "Unsupported prompt-cache"):
            estimate_maximum_call_cost(
                load_pricing_policy(),
                model_name="gpt-5.6",
                maximum_input_tokens=1,
                maximum_output_tokens=1,
                prompt_cache_policy="invented",
            )

    def test_usage_cost_separates_cache_reads_writes_and_ordinary_input(self) -> None:
        cost = calculate_usage_cost(
            load_pricing_policy(),
            model_name="gpt-5.6-sol-2026-07-01",
            input_tokens=100_000,
            cached_input_tokens=20_000,
            cache_write_tokens=30_000,
            output_tokens=10_000,
        )
        self.assertEqual(cost.ordinary_input_tokens, 50_000)
        self.assertEqual(cost.cost_usd, Decimal("0.7475"))

    def test_unknown_or_malformed_policy_fails_closed(self) -> None:
        policy = load_pricing_policy()
        with self.assertRaisesRegex(ValueError, "no model match"):
            policy.model("unknown")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "policy.json"
            value = json.loads(policy.path.read_text(encoding="utf-8"))
            value["models"][1]["aliases"] = ["gpt-5.6"]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicated"):
                load_pricing_policy(path)

    def test_invalid_cache_partition_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            calculate_usage_cost(
                load_pricing_policy(),
                model_name="gpt-5.6",
                input_tokens=10,
                cached_input_tokens=8,
                cache_write_tokens=3,
                output_tokens=0,
            )

    def test_environment_can_select_an_exact_user_supplied_policy(self) -> None:
        default = load_pricing_policy()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "pricing.json"
            path.write_bytes(default.path.read_bytes())
            with patch.dict(os.environ, {"CUDA_FRACTAL_OPENAI_PRICING_POLICY": str(path)}):
                selected = load_pricing_policy()
            self.assertEqual(selected.path, path.resolve())
            self.assertEqual(selected.sha256, default.sha256)


if __name__ == "__main__":
    unittest.main()
