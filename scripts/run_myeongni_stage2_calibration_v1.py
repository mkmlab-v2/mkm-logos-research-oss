#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "myeongni_stage2_calibration_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _decision(direction: float, confidence_adj: float, hold_cut: float, reduce_dir_cut: float, reduce_conf_cut: float) -> str:
    if confidence_adj < hold_cut:
        return "HOLD"
    if abs(direction) >= reduce_dir_cut and confidence_adj >= reduce_conf_cut:
        return "REDUCE"
    return "WATCH"


def _load_samples(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(doc, dict) or str(doc.get("schema")) != "mkm_myeongni_response_v2":
            continue
        core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
        coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
        final = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
        rows.append(
            {
                "source": str(p),
                "direction": _f(core.get("direction_core"), 0.0),
                "confidence_adjusted": _f(coord.get("confidence_adjusted"), _f(core.get("confidence_core"), 0.5)),
                "label": str(final.get("decision") or "WATCH").upper(),
            }
        )
    return rows


def _default_input_paths() -> list[Path]:
    return [
        ART / "mkm_myeongni_response_v2_latest.json",
        ART / "mkm_myeongni_response_v2_package_b_latest.json",
        ART / "mkm_myeongni_response_v2_package_b_attack_latest.json",
    ]


def _grid(start: float, stop: float, step: float) -> list[float]:
    out: list[float] = []
    x = start
    while x <= stop + 1e-9:
        out.append(round(x, 6))
        x += step
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Stage-2 calibration for myeongni response v2 from real artifacts.")
    ap.add_argument("--inputs-json", nargs="*", default=[], help="Optional explicit input JSON paths.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    input_paths = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.inputs_json] if args.inputs_json else _default_input_paths()
    samples = _load_samples(input_paths)
    if not samples:
        raise SystemExit("no usable mkm_myeongni_response_v2 samples found")

    hold_grid = _grid(0.32, 0.48, 0.02)
    reduce_dir_grid = _grid(0.30, 0.70, 0.02)
    reduce_conf_grid = _grid(0.48, 0.80, 0.02)

    best: dict[str, Any] | None = None
    for h in hold_grid:
        for rd in reduce_dir_grid:
            for rc in reduce_conf_grid:
                tp = 0
                for s in samples:
                    pred = _decision(float(s["direction"]), float(s["confidence_adjusted"]), h, rd, rc)
                    if pred == s["label"]:
                        tp += 1
                acc = tp / len(samples)
                preds = [_decision(float(s["direction"]), float(s["confidence_adjusted"]), h, rd, rc) for s in samples]
                # Encourage non-collapse to all WATCH while preserving agreement.
                unique_count = len(set(preds))
                collapse_penalty = 0.2 if unique_count == 1 else 0.0
                score = acc - collapse_penalty
                cand = {
                    "hold_confidence_cut": h,
                    "reduce_direction_cut": rd,
                    "reduce_confidence_cut": rc,
                    "accuracy_vs_current_labels": round(acc, 6),
                    "unique_pred_decisions": unique_count,
                    "score": round(score, 6),
                }
                if best is None or cand["score"] > best["score"]:
                    best = cand

    assert best is not None
    rows = []
    for s in samples:
        pred = _decision(
            float(s["direction"]),
            float(s["confidence_adjusted"]),
            float(best["hold_confidence_cut"]),
            float(best["reduce_direction_cut"]),
            float(best["reduce_confidence_cut"]),
        )
        rows.append(
            {
                "source": s["source"],
                "direction": s["direction"],
                "confidence_adjusted": s["confidence_adjusted"],
                "label_current": s["label"],
                "label_recalibrated": pred,
            }
        )

    out = {
        "schema": "myeongni_stage2_calibration_report_v1",
        "generated_at_utc": _now(),
        "inputs": [str(p) for p in input_paths],
        "sample_count": len(samples),
        "best_thresholds": best,
        "rows": rows,
        "note": "Weak-supervision calibration from current real artifacts; expand with larger historical/eval set for production locking.",
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "sample_count": len(samples), "best": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
