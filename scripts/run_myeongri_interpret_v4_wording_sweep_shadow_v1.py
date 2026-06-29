#!/usr/bin/env python3
"""Shadow replay: guard448 preds + wording_sweep postprocess (no preds overwrite)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_interpret_envelope_views_v1 import extract_compact_from_interpret_instruction  # noqa: E402
from scripts.run_myeongri_harness_v2_engine_interpret_smoke_v1 import _try_parse_envelope  # noqa: E402

DEFAULT_PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
DEFAULT_SFT = ROOT / "data/training/myeongri_interpret_sft_v4/locked_eval.jsonl"
DEFAULT_CAL30 = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v4_wording_sweep_shadow_latest.json"

_OVERCONF = re.compile(r"(정확한\s*해석|확실|확定적|모든\s*정보가\s*일치)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preds-jsonl", type=Path, default=DEFAULT_PREDS)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_SFT)
    ap.add_argument("--calibration30-json", type=Path, default=DEFAULT_CAL30)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all-rows", action="store_true", help="Replay all 100 rows (default: calibration30 only)")
    args = ap.parse_args()

    preds = _load_jsonl(args.preds_jsonl)
    sft = _load_jsonl(args.sft_jsonl)
    cal = json.loads(args.calibration30_json.read_text(encoding="utf-8"))
    target_rows = {int(s["row_index"]) for s in cal.get("samples") or []}
    if args.all_rows:
        target_rows = set(range(1, len(preds) + 1))

    improved = unchanged = 0
    rows_out: list[dict] = []
    for i, pred in enumerate(preds):
        ri = i + 1
        if ri not in target_rows:
            continue
        sft_row = sft[i]
        gold = json.loads(str(sft_row.get("output", "{}")))
        compact = extract_compact_from_interpret_instruction(str(sft_row.get("instruction", "")))
        raw = str(pred.get("prediction_raw", ""))
        p0, _, _ = _try_parse_envelope(
            raw,
            gold_out=gold,
            compact=compact,
            deterministic_input_sha256=str(gold.get("deterministic_input_sha256") or ""),
            wording_sweep_v1=False,
        )
        p1, _, _ = _try_parse_envelope(
            raw,
            gold_out=gold,
            compact=compact,
            deterministic_input_sha256=str(gold.get("deterministic_input_sha256") or ""),
            wording_sweep_v1=True,
        )
        ins0 = str((p0 or {}).get("mkm_advanced_insight") or "")
        ins1 = str((p1 or {}).get("mkm_advanced_insight") or "")
        flag0 = bool(_OVERCONF.search(ins0))
        flag1 = bool(_OVERCONF.search(ins1))
        changed = ins1 != ins0
        if changed:
            improved += 1
        else:
            unchanged += 1
        rows_out.append(
            {
                "row_index": ri,
                "insight_changed": changed,
                "overconfidence_before": flag0,
                "overconfidence_after": flag1,
                "sweep_notes": (p1 or {}).get("wording_sweep_postprocess_v1"),
            }
        )

    report = {
        "schema": "myeongri_interpret_v4_wording_sweep_shadow_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "preds_jsonl": str(args.preds_jsonl).replace("\\", "/"),
        "rows_replayed": len(rows_out),
        "insight_changed_count": improved,
        "unchanged_count": unchanged,
        "overconfidence_flags_before": sum(1 for r in rows_out if r["overconfidence_before"]),
        "overconfidence_flags_after": sum(1 for r in rows_out if r["overconfidence_after"]),
        "rows": rows_out,
        "track_wall": {"preds_mutated": False, "track_a_live_auto_merge": False},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "rows": len(rows_out),
                "changed": improved,
                "overconfidence_after": report["overconfidence_flags_after"],
                "out": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
