#!/usr/bin/env python3
"""Run k-expansion sweep (500/1000/2000) for W3 with effective-k tracking.

This is a reproducibility sweep for gate evaluation. If candidate rows are fewer
than requested k, `effective_k` is capped and recorded explicitly.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT_STR = str(Path(__file__).resolve().parents[1])
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
INPUT = ART / "W3_PILOT_BATCH_INPUT_V1.json"
INPUT_FALLBACK = ART / "W3_PILOT_BATCH_INPUT_V4.json"
SPEC = ART / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
OUT = ART / "W3_K_SWEEP_500_1000_2000_V1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    input_path = INPUT_FALLBACK if INPUT_FALLBACK.is_file() else INPUT
    input_doc = _load(input_path)
    base_spec = _load(SPEC)
    sample_count = len(input_doc.get("macro_lane_samples") or []) + len(input_doc.get("personal_lane_samples") or [])
    requests = [500, 1000, 2000]
    rows: list[dict[str, Any]] = []

    with TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for req_k in requests:
            effective_k = min(req_k, sample_count)
            promotion_eval_k = min(effective_k, 20)
            spec_doc = json.loads(json.dumps(base_spec))
            spec_doc["compute_contract"]["top_n"]["default_n"] = promotion_eval_k
            spec_doc["compute_contract"]["top_n"]["max_n"] = max(effective_k, 20)

            spec_tmp = tmpdir / f"spec_k_{req_k}.json"
            out_tmp = tmpdir / f"result_k_{req_k}.json"
            _save(spec_tmp, spec_doc)
            result = run_compute(input_path, spec_tmp, out_tmp)

            fs = result.get("falsification_summary") or {}
            pg = result.get("promotion_gate") or {}
            rows.append(
                {
                    "requested_k": req_k,
                    "effective_k": effective_k,
                    "promotion_eval_k": promotion_eval_k,
                    "candidate_pool_size": sample_count,
                    "top_n_count": int((result.get("run_meta") or {}).get("top_n_count", 0)),
                    "promotion_gate_passed": bool(pg.get("passed", False)),
                    "false_equivalence_risk_count": int(fs.get("false_equivalence_risk_count", 0)),
                    "deterministic_wording_risk_count": int(fs.get("deterministic_wording_risk_count", 0)),
                }
            )

    out_doc = {
        "schema": "w3_k_sweep_500_1000_2000_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_ref": str(input_path).replace("\\", "/"),
        "base_spec_ref": str(SPEC).replace("\\", "/"),
        "summary": {
            "candidate_pool_size": sample_count,
            "requested_ks": requests,
            "all_promotion_gates_passed": all(r["promotion_gate_passed"] for r in rows),
            "note": "effective_k is capped by candidate_pool_size when requested_k exceeds available candidates."
        },
        "runs": rows,
    }
    _save(OUT, out_doc)
    print("OK: W3 k-expansion sweep generated")
    print(f"out={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
