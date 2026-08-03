from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cuda_fractal_state_tool.automated_context import (
    build_round_review_ledger,
    ledger_transport_resource,
)
from cuda_fractal_state_tool.automated_protocol import PacketAuthorityBinding


class AutomatedContextTests(unittest.TestCase):
    def test_review_ledger_binds_exact_decision_override_proof_and_packets(self) -> None:
        author = PacketAuthorityBinding("packet-a", "a" * 64, "finding-a")
        derived = PacketAuthorityBinding("packet-b", "b" * 64, "finding-b")
        decision = "Selected experiment and locked prediction.\n```json\n{}\n```"
        override = '{"params":{"x":1}}'
        proof = SimpleNamespace(
            proof_id="proof-1",
            status="replay_proven",
            message="proven",
            receipt_sha256="c" * 64,
            engine_candidate_sha256="d" * 64,
            candidate_frame_sha256="e" * 64,
            replay_state_sha256="f" * 64,
            replay_frame_sha256="0" * 64,
        )
        materialization = SimpleNamespace(
            changed_paths=(SimpleNamespace(path="params.x", conceptual_domain="dynamics"),)
        )
        ledger = build_round_review_ledger(
            round_number=1,
            author_packet=author,
            derived_packet=derived,
            author_response_text=decision,
            override_text=override,
            materialization=materialization,
            proof=proof,
        )
        value = json.loads(ledger.payload)
        self.assertEqual(value["author_packet"]["packet_id"], "packet-a")
        self.assertEqual(value["derived_packet"]["packet_id"], "packet-b")
        self.assertEqual(value["author_decision_record"]["exact_text"], decision)
        self.assertEqual(value["state_override"]["exact_text"], override)
        self.assertEqual(value["proof"]["proof_id"], "proof-1")
        self.assertEqual(hashlib.sha256(ledger.payload).hexdigest(), ledger.sha256)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.json"
            path.write_bytes(ledger.payload)
            resource = ledger_transport_resource(path, ledger)
            self.assertEqual(resource.role, "controller_round_review_ledger")
            self.assertEqual(resource.payload, ledger.payload)


if __name__ == "__main__":
    unittest.main()
