#!/usr/bin/env python3
"""Run controlled 3-pass W3 batch compute and emit per-run artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys

ROOT_STR = str(Path(__file__).resolve().parents[1])
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from scripts.run_w3_resonance_compute import run_compute


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
BASE_INPUT = ART / "W3_PILOT_BATCH_INPUT_V1.json"
SPEC_PATH = ART / "W3_RESONANCE_COMPUTE_SPEC_V1.json"
CURATED_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_summary_latest.json"
CURATED_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_curated_latest.jsonl"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_jsonl(path: Path):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _dynamic_target_total() -> int:
    if not CURATED_SUMMARY.is_file():
        return 24
    doc = _load(CURATED_SUMMARY)
    curated = int(doc.get("curated_count", 20))
    # Scale with curated pool while keeping runtime bounded.
    return max(24, min(240, curated // 2))


def _expand_lane(rows: list[dict[str, Any]], target_count: int, *, lane: str, idx: int, symbol_pool: list[str]) -> list[dict[str, Any]]:
    if not rows:
        return []
    out: list[dict[str, Any]] = []
    for i in range(target_count):
        base = dict(rows[i % len(rows)])
        sym = symbol_pool[i % len(symbol_pool)] if symbol_pool else ""
        if lane == "macro":
            base["sample_id"] = f"W3_MACRO_V{idx}_{i+1:03d}"
            base["run_id"] = f"w3_macro_v{idx}_{i+1:03d}"
            base["myeongri_cycle"] = f"{base.get('myeongri_cycle','cycle_stub')}_v{idx}_{i+1:03d}"
            if sym:
                base["logos_symbol_ref"] = sym
            base["rationale"] = f"[HYPO] Multi-batch v{idx} macro sample {i+1}."
        else:
            base["sample_id"] = f"W3_PERSONAL_V{idx}_{i+1:03d}"
            base["personal_run_id"] = f"w3_personal_v{idx}_{i+1:03d}"
            base["scenario_desc"] = f"Multi-batch v{idx} personal scenario {i+1}."
            base["rationale"] = f"[HYPO] Multi-batch v{idx} personal sample {i+1}."
            if sym:
                base["canonical_ref"] = sym
        out.append(base)
    return out


def _variant_doc(base: dict[str, Any], idx: int) -> dict[str, Any]:
    out = json.loads(json.dumps(base))
    out["schema"] = "w3_pilot_batch_input_v1"
    out["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out["status"] = f"batch_ready_v{idx}"
    out["notes"] = [
        f"Controlled multi-batch variant v{idx}.",
        "No A-track promotion claim is made in this artifact.",
    ]
    target_total = _dynamic_target_total()
    macro_target = max(12, target_total // 2)
    personal_target = max(12, target_total - macro_target)
    symbol_pool = [str(r.get("symbol", "")).strip() for r in _iter_jsonl(CURATED_JSONL) or []]
    symbol_pool = [s for s in symbol_pool if s]
    out["macro_lane_samples"] = _expand_lane(
        list(out.get("macro_lane_samples") or []),
        macro_target,
        lane="macro",
        idx=idx,
        symbol_pool=symbol_pool,
    )
    out["personal_lane_samples"] = _expand_lane(
        list(out.get("personal_lane_samples") or []),
        personal_target,
        lane="personal",
        idx=idx,
        symbol_pool=symbol_pool,
    )
    out["scaling_meta"] = {
        "target_total": target_total,
        "macro_target": macro_target,
        "personal_target": personal_target,
        "symbol_pool_size": len(symbol_pool),
    }
    return out


def main() -> int:
    base = _load(BASE_INPUT)
    run_log: list[dict[str, Any]] = []
    # Regenerate V1 baseline with current compute contract (including aux metadata).
    v1_output_path = ART / "W3_RESONANCE_BATCH_RESULT_V1.json"
    v1_out = run_compute(BASE_INPUT, SPEC_PATH, v1_output_path)
    run_log.append(
        {
            "variant": "V1",
            "input": str(BASE_INPUT).replace("\\", "/"),
            "output": str(v1_output_path).replace("\\", "/"),
            "top_n_count": int((v1_out.get("run_meta") or {}).get("top_n_count", 0)),
            "promotion_gate_passed": bool((v1_out.get("promotion_gate") or {}).get("passed", False)),
            "false_equivalence_risk_count": int(
                (v1_out.get("falsification_summary") or {}).get("false_equivalence_risk_count", 0)
            ),
            "deterministic_wording_risk_count": int(
                (v1_out.get("falsification_summary") or {}).get("deterministic_wording_risk_count", 0)
            ),
        }
    )

    for idx in (2, 3, 4):
        input_path = ART / f"W3_PILOT_BATCH_INPUT_V{idx}.json"
        output_path = ART / f"W3_RESONANCE_BATCH_RESULT_V{idx}.json"
        in_doc = _variant_doc(base, idx)
        _save(input_path, in_doc)
        out = run_compute(input_path, SPEC_PATH, output_path)
        run_log.append(
            {
                "variant": f"V{idx}",
                "input": str(input_path).replace("\\", "/"),
                "output": str(output_path).replace("\\", "/"),
                "top_n_count": int((out.get("run_meta") or {}).get("top_n_count", 0)),
                "promotion_gate_passed": bool((out.get("promotion_gate") or {}).get("passed", False)),
                "false_equivalence_risk_count": int(
                    (out.get("falsification_summary") or {}).get("false_equivalence_risk_count", 0)
                ),
                "deterministic_wording_risk_count": int(
                    (out.get("falsification_summary") or {}).get("deterministic_wording_risk_count", 0)
                ),
            }
        )
    log_path = ART / "W3_MULTI_BATCH_RUN_LOG_V1.json"
    _save(
        log_path,
        {
            "schema": "w3_multi_batch_run_log_v1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "runs": run_log,
        },
    )
    print("OK: W3 multi-batch run complete")
    print(f"log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
