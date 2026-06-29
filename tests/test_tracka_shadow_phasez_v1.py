from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "scripts/extract_logic_weights_for_track_a_v1.py"
REPORT = ROOT / "scripts/report_optimization_impact_v1.py"


def test_extract_logic_weights_smoke(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "checks": [
                    {"unit_id": "u_policy_safety", "v_score": 1, "reason": "citation_lock_subset_ok", "citations": ["Jhn.1.1"]}
                ]
            }
        ),
        encoding="utf-8",
    )
    shadow = tmp_path / "shadow.json"
    shadow.write_text(
        json.dumps({"rows": [{"verse_id": "Jhn.1.1", "primary_tag": "소양", "confidence": 0.92}]}),
        encoding="utf-8",
    )
    psi = tmp_path / "psi.json"
    psi.write_text(
        json.dumps(
            {
                "logic_graph": {
                    "nodes": [
                        {"type": "Constraints", "source_line_preview": "policy safety traceability evidence"},
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "weights.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(EXTRACT),
            "--path-gate",
            str(gate),
            "--shadow",
            str(shadow),
            "--psi",
            str(psi),
            "--max-terms",
            "16",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["selected_terms"] > 0
    assert isinstance(doc["must_keep_terms_shadow"], list)


def test_optimization_report_build_smoke(tmp_path: Path) -> None:
    perf = tmp_path / "perf.json"
    perf.write_text(
        json.dumps(
            {
                "raw_baseline": {"metrics": {"global_token_saving_rate": 0.2, "avg_reconstruction_fidelity_jaccard": 0.8, "avg_sensitive_integrity": 1.0}},
                "logic_aware_shadow": {
                    "metrics": {"global_token_saving_rate": 0.19, "avg_reconstruction_fidelity_jaccard": 0.81, "avg_sensitive_integrity": 1.0}
                },
                "delta_shadow_minus_raw": {
                    "global_token_saving_rate": -0.01,
                    "avg_reconstruction_fidelity_jaccard": 0.01,
                    "avg_sensitive_integrity": 0.0,
                },
                "logic_aware_terms_count": 7,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "impact.json"
    md = tmp_path / "impact.md"
    cp = subprocess.run(
        [sys.executable, str(REPORT), "--perf", str(perf), "--out", str(out), "--out-md", str(md)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "optimization_impact_v1"
    assert doc["delta_shadow_minus_raw"]["avg_reconstruction_fidelity_jaccard"] == 0.01
