from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from cuda_fractal_state_tool.async_jobs import AsyncJobRunner, JobRequestIdentity
from cuda_fractal_state_tool.preview_service import PreviewPolicy, PreviewService
from cuda_fractal_state_tool.preview_worker import create_preview


class PreviewServiceTests(unittest.TestCase):
    def _run_preview(self, service: PreviewService, source: Path, cache: Path):
        callbacks = []
        runner = AsyncJobRunner(callbacks.append, max_workers=1, max_pending_jobs=2)
        runner.submit(
            "preview",
            JobRequestIdentity(generation=1),
            lambda context: service.prepare(source, cache, context),
            lambda outcome: callbacks.append(outcome),
        )
        deadline = time.time() + 10
        while not callbacks and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(callbacks)
        callbacks.pop(0)()
        outcome = callbacks.pop(0)
        runner.shutdown(wait=True)
        if outcome.error:
            raise AssertionError(outcome.error)
        return outcome.value

    def test_subprocess_preview_is_bounded_atomic_and_cached(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "frame.png"
            Image.new("RGB", (1000, 500), (20, 40, 60)).save(source)
            service = PreviewService(PreviewPolicy(timeout_seconds=10))
            first = self._run_preview(service, source, root / "cache")
            second = self._run_preview(service, source, root / "cache")
            self.assertEqual((first.preview_width, first.preview_height), (640, 320))
            self.assertFalse(first.cache_hit)
            self.assertTrue(second.cache_hit)
            self.assertEqual(first.preview_sha256, second.preview_sha256)
            self.assertFalse(list((root / "cache").glob("*.tmp.*")))

    def test_worker_never_upscales_and_rejects_pixel_and_corrupt_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            small = root / "small.bmp"
            Image.new("RGB", (20, 10), (1, 2, 3)).save(small)
            payload = create_preview(small, root / "small.png", 640, 480, 1_000, 100)
            self.assertEqual((payload["preview_width"], payload["preview_height"]), (20, 10))
            self.assertFalse(payload["upscaled"])

            large = root / "large.png"
            Image.new("RGB", (50, 50), (1, 2, 3)).save(large)
            with self.assertRaisesRegex(ValueError, "pixel count exceeds"):
                create_preview(large, root / "large-preview.png", 640, 480, 2_000, 100)

            corrupt = root / "corrupt.png"
            corrupt.write_bytes(b"not an image")
            with self.assertRaises(Exception):
                create_preview(corrupt, root / "corrupt-preview.png", 640, 480, 2_000, 100)


if __name__ == "__main__":
    unittest.main()
