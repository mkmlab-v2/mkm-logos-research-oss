from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_lora_domain_architecture_sweep_v1_runs() -> None:
    out = ROOT / "reports" / "tmp_lora_domain_architecture_sweep_test.json"
    if out.exists():
        out.unlink()
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_lora_domain_architecture_sweep_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lora_domain_architecture_sweep_v1"
    assert doc["case_count"] == 40
    assert doc["verdict"]["vision_is_optimal"] is False
    assert doc["verdict"]["best_candidate_id"] not in {"minimal_3x7", "vision_20x200_flat"}
    uplift = doc.get("hybrid_routing_uplift", {})
    assert uplift.get("K75_hybrid_hit_rate", 0) >= uplift.get("K75_formula_only_hit_rate", 0)
    ranked = doc["architectures_ranked"]
    assert ranked[0]["score"]["composite_score"] >= ranked[-1]["score"]["composite_score"]
