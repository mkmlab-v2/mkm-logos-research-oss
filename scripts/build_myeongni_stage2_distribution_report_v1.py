#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CAL = ART / "myeongni_stage2_calibration_report_latest.json"
DEFAULT_BASE = ART / "mkm_myeongni_response_v2_stage2_baseline_latest.json"
DEFAULT_OVR = ART / "myeongni_stage2_threshold_override_latest.json"
DEFAULT_OUT = ART / "myeongni_stage2_distribution_stability_report_latest.json"
DEFAULT_REALSET_DIR = ART / "myeongni_stage2_realset"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _decision(direction: float, confidence_adj: float, hold_cut: float, reduce_dir_cut: float, reduce_conf_cut: float) -> str:
    if confidence_adj < hold_cut:
        return "HOLD"
    if abs(direction) >= reduce_dir_cut and confidence_adj >= reduce_conf_cut:
        return "REDUCE"
    return "WATCH"


def _ratio(counts: dict[str, int], n: int) -> dict[str, float]:
    if n <= 0:
        return {"HOLD": 0.0, "WATCH": 0.0, "REDUCE": 0.0}
    return {k: round(counts.get(k, 0) / n, 6) for k in ("HOLD", "WATCH", "REDUCE")}


def _load_response_rows_from_dir(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_dir():
        return rows
    for p in sorted(path.glob("*.json")):
        try:
            doc = _read_json(p)
        except Exception:
            continue
        if str(doc.get("schema") or "") != "mkm_myeongni_response_v2":
            continue
        core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
        coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
        rows.append(
            {
                "source": str(p.resolve()),
                "direction": _f(core.get("direction_core"), 0.0),
                "confidence_adjusted": _f(coord.get("confidence_adjusted"), _f(core.get("confidence_core"), 0.5)),
                "synthetic": False,
            }
        )
    return rows


def _expand_rows(base_rows: list[dict[str, Any]], target_count: int, seed: int) -> tuple[list[dict[str, Any]], int]:
    if len(base_rows) >= target_count:
        return base_rows[:], 0
    rng = random.Random(seed)
    out = [dict(r) for r in base_rows]
    synthetic = 0
    while len(out) < target_count:
        src = base_rows[len(out) % len(base_rows)]
        d = _clip(_f(src.get("direction"), 0.0) + rng.uniform(-0.08, 0.08), -1.0, 1.0)
        c = _clip(_f(src.get("confidence_adjusted"), 0.5) + rng.uniform(-0.06, 0.06), 0.0, 1.0)
        out.append(
            {
                "source": str(src.get("source") or "synthetic"),
                "direction": round(d, 6),
                "confidence_adjusted": round(c, 6),
                "synthetic": True,
            }
        )
        synthetic += 1
    return out, synthetic


def main() -> int:
    ap = argparse.ArgumentParser(description="Build GO/WATCH/HOLD distribution stability report for stage2 thresholds.")
    ap.add_argument("--calibration-json", type=Path, default=DEFAULT_CAL)
    ap.add_argument("--baseline-json", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--override-json", type=Path, default=DEFAULT_OVR)
    ap.add_argument("--realset-dir", type=Path, default=DEFAULT_REALSET_DIR)
    ap.add_argument("--target-sample-count", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    cal_path = args.calibration_json if args.calibration_json.is_absolute() else ROOT / args.calibration_json
    base_path = args.baseline_json if args.baseline_json.is_absolute() else ROOT / args.baseline_json
    ovr_path = args.override_json if args.override_json.is_absolute() else ROOT / args.override_json
    realset_dir = args.realset_dir if args.realset_dir.is_absolute() else ROOT / args.realset_dir
    cal = _read_json(cal_path)
    base = _read_json(base_path)
    ovr = _read_json(ovr_path)

    base_rows = _load_response_rows_from_dir(realset_dir)
    source_mode = "realset_dir"
    rows = cal.get("rows") if isinstance(cal.get("rows"), list) else []
    if not base_rows:
        # Fallback for early stage where realset directory is not populated yet.
        base_rows = [
            {
                "source": str(r.get("source") or ""),
                "direction": _f(r.get("direction"), 0.0),
                "confidence_adjusted": _f(r.get("confidence_adjusted"), 0.5),
                "synthetic": False,
            }
            for r in rows
        ]
        source_mode = "calibration_rows_fallback"
    if not base_rows:
        raise SystemExit("no calibration rows found")

    expanded_rows, synthetic_count = _expand_rows(base_rows, max(1, int(args.target_sample_count)), int(args.seed))

    bcal = base.get("calibration") if isinstance(base.get("calibration"), dict) else {}
    ot = ovr.get("thresholds") if isinstance(ovr.get("thresholds"), dict) else {}
    b_hold = _f(bcal.get("hold_confidence_cut"), 0.42)
    b_rd = _f(bcal.get("reduce_direction_cut"), 0.55)
    b_rc = _f(bcal.get("reduce_confidence_cut"), 0.66)
    a_hold = _f(ot.get("hold_confidence_cut"), b_hold)
    a_rd = _f(ot.get("reduce_direction_cut"), b_rd)
    a_rc = _f(ot.get("reduce_confidence_cut"), b_rc)

    counts_before = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    counts_after = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    transitions: dict[str, int] = {}
    for r in expanded_rows:
        d = _f(r.get("direction"), 0.0)
        c = _f(r.get("confidence_adjusted"), 0.5)
        b = _decision(d, c, b_hold, b_rd, b_rc)
        a = _decision(d, c, a_hold, a_rd, a_rc)
        counts_before[b] += 1
        counts_after[a] += 1
        key = f"{b}->{a}"
        transitions[key] = transitions.get(key, 0) + 1

    n = len(expanded_rows)
    ratio_before = _ratio(counts_before, n)
    ratio_after = _ratio(counts_after, n)
    watch_bias_delta = round(ratio_after["WATCH"] - ratio_before["WATCH"], 6)

    out = {
        "schema": "myeongni_stage2_distribution_stability_report_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "calibration_json": str(cal_path.resolve()),
            "baseline_json": str(base_path.resolve()),
            "override_json": str(ovr_path.resolve()),
        },
        "sample_set": {
            "total_count": n,
            "real_count": len(base_rows),
            "synthetic_count": synthetic_count,
            "seed": int(args.seed),
            "target_sample_count": int(args.target_sample_count),
            "source_mode": source_mode,
            "realset_dir": str(realset_dir.resolve()),
        },
        "thresholds": {
            "before": {
                "hold_confidence_cut": round(b_hold, 6),
                "reduce_direction_cut": round(b_rd, 6),
                "reduce_confidence_cut": round(b_rc, 6),
            },
            "after": {
                "hold_confidence_cut": round(a_hold, 6),
                "reduce_direction_cut": round(a_rd, 6),
                "reduce_confidence_cut": round(a_rc, 6),
            },
        },
        "distribution": {
            "before_counts": counts_before,
            "before_ratio": ratio_before,
            "after_counts": counts_after,
            "after_ratio": ratio_after,
            "watch_bias_delta": watch_bias_delta,
        },
        "transitions": transitions,
        "note": "Synthetic expansion is for stability probing only. Production lock requires 50+ real artifacts.",
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "total": n, "real": len(base_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
