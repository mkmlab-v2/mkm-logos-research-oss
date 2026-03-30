#!/usr/bin/env python3
"""Sweep false-equivalence threshold gate values and record decision changes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import sys

ROOT_STR = str(Path(__file__).resolve().parents[1])
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
INPUT = ART / "W3_PILOT_BATCH_INPUT_V1.json"
SPEC = ART / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
OUT = ART / "W3_GATE_THRESHOLD_SWEEP_V1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    base_spec = _load(SPEC)
    results = []
    with TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for thresh in (0, 1, 2):
            spec_doc = json.loads(json.dumps(base_spec))
            spec_doc["output_contract"]["promotion_gate"]["false_equivalence_max_count"] = thresh
            spec_tmp = tmpdir / f"spec_{thresh}.json"
            out_tmp = tmpdir / f"out_{thresh}.json"
            _save(spec_tmp, spec_doc)
            out = run_compute(INPUT, spec_tmp, out_tmp)
            fs = out.get("falsification_summary") or {}
            pg = out.get("promotion_gate") or {}
            results.append(
                {
                    "false_equivalence_max_count": thresh,
                    "promotion_gate_passed": bool(pg.get("passed", False)),
                    "false_equivalence_risk_count": int(fs.get("false_equivalence_risk_count", 0)),
                    "deterministic_wording_risk_count": int(fs.get("deterministic_wording_risk_count", 0)),
                }
            )

    decision_changes = []
    prev = None
    for r in results:
        cur = r["promotion_gate_passed"]
        if prev is not None and cur != prev:
            decision_changes.append(
                {
                    "from_threshold": results[results.index(r) - 1]["false_equivalence_max_count"],
                    "to_threshold": r["false_equivalence_max_count"],
                    "decision_changed_to": cur,
                }
            )
        prev = cur

    out_doc = {
        "schema": "w3_gate_threshold_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_ref": str(INPUT).replace("\\", "/"),
        "base_spec_ref": str(SPEC).replace("\\", "/"),
        "results": results,
        "decision_changes": decision_changes,
    }
    _save(OUT, out_doc)
    print("OK: W3 threshold sweep generated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
