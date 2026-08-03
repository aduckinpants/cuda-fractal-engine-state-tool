from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path
from typing import Optional

from .async_jobs import AsyncJobRunner, JobRequestIdentity
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .scalar_sweep import ScalarBracketSweepService, ScalarSweepPlanError


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one bounded local scalar bracket through ordinary state-override proofs"
    )
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--fixed-override", type=Path)
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    parser.add_argument("--sweeps-root", type=Path)
    parser.add_argument(
        "--runtime-compatibility", choices=("development", "strict"), default=None
    )
    args = parser.parse_args(argv)
    try:
        plan_text = args.plan.read_bytes().decode("utf-8")
        fixed_text = (
            args.fixed_override.read_bytes().decode("utf-8") if args.fixed_override else "{}"
        )
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"status": "sweep_error", "error": str(exc)}, indent=2))
        return 2

    completed = threading.Event()
    box = []
    runner = AsyncJobRunner(lambda callback: callback(), max_workers=1, max_pending_jobs=1)

    def completion(outcome):
        box.append(outcome)
        completed.set()

    try:
        runner.submit(
            "scalar_sweep",
            JobRequestIdentity(generation=0, packet_id=args.packet_dir.resolve().name),
            lambda job: ScalarBracketSweepService().execute(
                packet_dir=args.packet_dir,
                fixed_override_text=fixed_text,
                plan_text=plan_text,
                runtime_cmd_path=args.runtime_cmd,
                job=job,
                sweeps_root=args.sweeps_root,
                runtime_compatibility_mode=args.runtime_compatibility,
            ),
            completion,
        )
        if not completed.wait(24 * 60 * 60):
            raise TimeoutError("Scalar sweep worker did not complete")
        outcome = box[0]
        if outcome.cancelled:
            print(json.dumps({"status": "CANCELLED"}, indent=2))
            return 3
        if outcome.error:
            raise ScalarSweepPlanError(outcome.error)
        result = outcome.value
    except (ScalarSweepPlanError, OSError, ValueError, TimeoutError) as exc:
        print(json.dumps({"status": "sweep_error", "error": str(exc)}, indent=2))
        return 2
    finally:
        runner.shutdown(wait=False)

    print(
        json.dumps(
            {
                "status": result.disposition,
                "sweep_id": result.sweep_id,
                "sweep_dir": str(result.sweep_dir),
                "receipt_path": str(result.receipt_path),
                "members": [
                    {"index": item.index, "value": item.value, "status": item.status}
                    for item in result.members
                ],
                "human_acceptance": False,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if result.disposition == "COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
