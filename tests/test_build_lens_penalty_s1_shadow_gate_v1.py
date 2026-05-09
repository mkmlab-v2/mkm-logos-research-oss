from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_lens_penalty_s1_shadow_gate_v1_go_review(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_lens_penalty_s1_shadow_gate_v1.py"

    comparator = tmp_path / "comparator.json"
    policy = tmp_path / "policy.json"
    out = tmp_path / "gate.json"

    comparator.write_text(
        json.dumps({"summary": {"simulated_strict_gap": -0.1, "flip_candidates": 2}}),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps({"human_review_required": True}),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--comparator-json",
            str(comparator),
            "--apply-policy-json",
            str(policy),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "GO_REVIEW"
    assert payload["all_green"] is True
