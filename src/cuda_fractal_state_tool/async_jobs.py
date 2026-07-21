from __future__ import annotations

import subprocess
import threading
import time
import uuid
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from .process_utils import ProcessResult, kill_process_tree


@dataclass(frozen=True)
class JobRequestIdentity:
    generation: int
    finding_id: Optional[str] = None
    authoring_base_sha256: Optional[str] = None
    packet_id: Optional[str] = None
    packet_sha256: Optional[str] = None
    packet_manifest_sha256: Optional[str] = None
    override_text_sha256: Optional[str] = None
    candidate_sha256: Optional[str] = None
    runtime_identity_sha256: Optional[str] = None
    ui_salt_contract_sha256: Optional[str] = None


@dataclass(frozen=True)
class JobOutcome:
    job_id: str
    kind: str
    identity: JobRequestIdentity
    value: Any = None
    error: Optional[str] = None
    cancelled: bool = False


class JobCancelledError(RuntimeError):
    pass


class WorkerQueueFullError(RuntimeError):
    pass


class JobContext:
    def __init__(self, runner: "AsyncJobRunner", job_id: str, cancel_event: threading.Event) -> None:
        self._runner = runner
        self.job_id = job_id
        self._cancel_event = cancel_event

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise JobCancelledError("Job was cancelled")

    def run_process(
        self,
        command: Sequence[str],
        cwd: Path,
        timeout_seconds: Optional[float] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> ProcessResult:
        self.raise_if_cancelled()
        start = time.monotonic()
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP") else 0
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd),
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags,
        )
        self._runner._register_process(self.job_id, process)
        timed_out = False
        try:
            while True:
                if self.cancelled:
                    kill_process_tree(process.pid)
                    process.communicate()
                    raise JobCancelledError("Job was cancelled while its owned process was running")
                elapsed = time.monotonic() - start
                if timeout_seconds is not None and elapsed >= timeout_seconds:
                    timed_out = True
                    kill_process_tree(process.pid)
                    stdout, stderr = process.communicate()
                    break
                try:
                    stdout, stderr = process.communicate(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    continue
        finally:
            self._runner._unregister_process(self.job_id, process)
        return ProcessResult(
            command=list(command),
            cwd=str(cwd),
            pid=process.pid,
            exit_code=process.returncode,
            timed_out=timed_out,
            elapsed_seconds=time.monotonic() - start,
            stdout=stdout,
            stderr=stderr,
            observed_process_tree=[],
        )


class AsyncJobRunner:
    def __init__(
        self,
        dispatcher: Callable[[Callable[[], None]], None],
        max_workers: int = 2,
        max_pending_jobs: int = 8,
    ) -> None:
        if max_workers < 1 or max_pending_jobs < max_workers:
            raise ValueError("Worker limits must allow at least one worker and one slot per worker")
        self._dispatcher = dispatcher
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fractal-state-ui")
        self._capacity = threading.BoundedSemaphore(max_pending_jobs)
        self._lock = threading.Lock()
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._processes: dict[str, set[subprocess.Popen[str]]] = {}
        self._closing = False

    def submit(
        self,
        kind: str,
        identity: JobRequestIdentity,
        operation: Callable[[JobContext], Any],
        completion: Callable[[JobOutcome], None],
    ) -> str:
        with self._lock:
            if self._closing:
                raise RuntimeError("Worker is shutting down")
        if not self._capacity.acquire(blocking=False):
            raise WorkerQueueFullError("Worker queue is full")
        job_id = uuid.uuid4().hex
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[job_id] = cancel_event

        def execute() -> JobOutcome:
            context = JobContext(self, job_id, cancel_event)
            try:
                value = operation(context)
                context.raise_if_cancelled()
                return JobOutcome(job_id=job_id, kind=kind, identity=identity, value=value)
            except JobCancelledError:
                return JobOutcome(job_id=job_id, kind=kind, identity=identity, cancelled=True)
            except Exception as exc:
                return JobOutcome(job_id=job_id, kind=kind, identity=identity, error=str(exc))

        future = self._executor.submit(execute)
        with self._lock:
            self._futures[job_id] = future

        def done(completed: Future[JobOutcome]) -> None:
            try:
                try:
                    outcome = completed.result()
                except CancelledError:
                    outcome = JobOutcome(
                        job_id=job_id,
                        kind=kind,
                        identity=identity,
                        cancelled=True,
                    )
            finally:
                with self._lock:
                    self._cancel_events.pop(job_id, None)
                    self._futures.pop(job_id, None)
                    should_dispatch = not self._closing
                self._capacity.release()
            if should_dispatch:
                self._dispatcher(lambda: completion(outcome))

        future.add_done_callback(done)
        return job_id

    def cancel_all(self) -> None:
        with self._lock:
            cancel_events = list(self._cancel_events.values())
            processes = [process for owned in self._processes.values() for process in owned]
            futures = list(self._futures.values())
        for event in cancel_events:
            event.set()
        for future in futures:
            future.cancel()
        for process in processes:
            if process.poll() is None:
                kill_process_tree(process.pid)

    def shutdown(self, wait: bool = False) -> None:
        with self._lock:
            if self._closing:
                return
            self._closing = True
        self.cancel_all()
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def _register_process(self, job_id: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._closing or job_id not in self._cancel_events:
                kill_process_tree(process.pid)
                raise JobCancelledError("Job no longer owns a process slot")
            self._processes.setdefault(job_id, set()).add(process)

    def _unregister_process(self, job_id: str, process: subprocess.Popen[str]) -> None:
        with self._lock:
            owned = self._processes.get(job_id)
            if owned is None:
                return
            owned.discard(process)
            if not owned:
                self._processes.pop(job_id, None)
