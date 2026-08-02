from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

from cuda_fractal_state_tool.async_jobs import AsyncJobRunner, JobRequestIdentity


class AsyncJobRunnerTests(unittest.TestCase):
    def test_completion_is_dispatched_with_exact_identity(self) -> None:
        callbacks = []
        runner = AsyncJobRunner(callbacks.append, max_workers=1, max_pending_jobs=2)
        identity = JobRequestIdentity(generation=4, finding_id="finding", authoring_base_sha256="base")
        runner.submit("example", identity, lambda context: "done", lambda outcome: callbacks.append(outcome))
        deadline = time.time() + 5
        while len(callbacks) < 1 and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(callbacks)
        dispatch = callbacks.pop(0)
        dispatch()
        outcome = callbacks.pop(0)
        self.assertEqual(outcome.value, "done")
        self.assertEqual(outcome.identity, identity)
        runner.shutdown(wait=True)

    def test_cancel_all_terminates_only_owned_process_and_marks_job_cancelled(self) -> None:
        callbacks = []
        runner = AsyncJobRunner(callbacks.append, max_workers=1, max_pending_jobs=2)
        started = threading.Event()

        def operation(context):
            started.set()
            return context.run_process(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=Path.cwd(),
                timeout_seconds=60,
            )

        runner.submit(
            "process",
            JobRequestIdentity(generation=1),
            operation,
            lambda outcome: callbacks.append(outcome),
        )
        self.assertTrue(started.wait(3))
        runner.cancel_all()
        deadline = time.time() + 8
        while not callbacks and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(callbacks)
        callbacks.pop(0)()
        outcome = callbacks.pop(0)
        self.assertTrue(outcome.cancelled)

    def test_cancel_one_job_does_not_cancel_an_unrelated_job(self) -> None:
        callbacks = []
        runner = AsyncJobRunner(callbacks.append, max_workers=2, max_pending_jobs=2)
        started = threading.Event()
        release = threading.Event()
        outcomes = []

        def waiting(context):
            started.set()
            while not release.wait(0.01):
                context.raise_if_cancelled()
            return "completed"

        first = runner.submit("one", JobRequestIdentity(generation=1), waiting, outcomes.append)
        runner.submit("two", JobRequestIdentity(generation=1), waiting, outcomes.append)
        self.assertTrue(started.wait(2.0))
        self.assertTrue(runner.cancel(first))
        release.set()
        deadline = time.time() + 3.0
        while len(callbacks) < 2 and time.time() < deadline:
            time.sleep(0.01)
        for callback in callbacks:
            callback()
        runner.shutdown(wait=True)
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(sum(outcome.cancelled for outcome in outcomes), 1)
        self.assertIn("completed", [outcome.value for outcome in outcomes])
        self.assertFalse(runner.cancel("missing-job"))
        runner.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
