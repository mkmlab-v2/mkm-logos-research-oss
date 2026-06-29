from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_logos_gate_closure_consistency_v1.py"


def test_gate_closure_consistency_smoke(tmp_path: Path) -> None:
    gate = {
        "tiers": {"L2_track_c_shadow_ingest": {"passed": True}},
        "metrics": {"weak_gold_hit_at_3": 0.916666667, "bridge_rag_evidence_n": 24},
    }
    closure = {
        "closure_ok": True,
        "checks": {"semantic_rag_quality": {"L2_passed": True, "weak_gold_hit_at_3": 0.916666667}},
    }
    gate_path = tmp_path / "gate.json"
    closure_path = tmp_path / "closure.json"
    out_path = tmp_path / "out.json"
    gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    closure_path.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-json",
            str(gate_path),
            "--closure-json",
            str(closure_path),
            "--out-json",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_gate_closure_consistency_v1"
    assert doc["ok"] is True
    assert all(doc["checks"].values())
