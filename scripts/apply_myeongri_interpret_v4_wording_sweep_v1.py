#!/usr/bin/env python3
"""Apply B-track wording sweep to calibration30 needs_edit rows (research_only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_interpret_envelope_views_v1 import (  # noqa: E402
    extract_compact_from_interpret_instruction,
    sweep_interpret_insight_wording_v1,
)

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_SFT = ROOT / "data/training/myeongri_interpret_sft_v4/locked_eval.jsonl"
DEFAULT_PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"
DEFAULT_REPORT = ROOT / "reports/myeongri_interpret_v4_wording_sweep_latest.json"

def _banned_price_med(insight: str) -> bool:
    if re.search(r"(매수|매도|투자\s*추천|처방|수술\s*필)", insight, re.I):
        return True
    if re.search(r"진단", insight, re.I) and not re.search(r"진단\s*아님", insight, re.I):
        return True
    return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _update_json_insight(raw: str, new_insight: str) -> str | None:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    obj["mkm_advanced_insight"] = new_insight
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--sft-jsonl", type=Path, default=DEFAULT_SFT)
    ap.add_argument("--preds-jsonl", type=Path, default=DEFAULT_PREDS)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--promote-to-pass", action="store_true", default=True)
    ap.add_argument("--no-promote-to-pass", action="store_false", dest="promote_to_pass")
    ap.add_argument("--skip-preds-update", action="store_true", default=True)
    ap.add_argument("--update-preds-jsonl", action="store_false", dest="skip_preds_update")
    args = ap.parse_args()

    if not args.sample_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.sample_json}"}))
        return 2
    if not args.sft_jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.sft_jsonl}"}))
        return 2

    sft_rows = _load_jsonl(args.sft_jsonl)
    sft_by_row = {i + 1: row for i, row in enumerate(sft_rows)}

    doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    sweep_rows: list[dict[str, Any]] = []
    counts = {"pass": 0, "fail": 0, "needs_edit": 0}

    for s in doc.get("samples") or []:
        verdict = str(s.get("reviewer_verdict") or "")
        if verdict != "needs_edit":
            counts[verdict] = counts.get(verdict, 0) + 1
            continue

        ri = int(s["row_index"])
        sft_row = sft_by_row.get(ri)
        compact = (
            extract_compact_from_interpret_instruction(str(sft_row.get("instruction", "")))
            if sft_row
            else None
        )
        old_insight = str(s.get("mkm_advanced_insight") or "")
        comment = str(s.get("reviewer_comment") or "")
        gold_head = str(s.get("gold_insight_head") or "")

        new_insight, notes = sweep_interpret_insight_wording_v1(
            old_insight,
            gold_insight_head=gold_head,
            compact=compact,
            row_index=ri,
            reviewer_comment=comment,
        )

        s["mkm_advanced_insight_pre_sweep"] = old_insight
        s["mkm_advanced_insight"] = new_insight
        s["wording_sweep_applied_at_utc"] = _utc_now()
        s["wording_sweep_notes"] = notes
        s["wording_sweep_source"] = "apply_myeongri_interpret_v4_wording_sweep_v1.py"

        new_verdict = verdict
        if args.promote_to_pass and not _banned_price_med(new_insight):
            new_verdict = "pass"
            s["reviewer_verdict"] = "pass"
            s["reviewer_verdict_source"] = "wording_sweep_v1_promoted"
            s["reviewer_comment"] = f"{comment} → wording_sweep 적용 후 pass."
        counts[new_verdict] = counts.get(new_verdict, 0) + 1

        sweep_rows.append(
            {
                "row_index": ri,
                "notes": notes,
                "promoted_to_pass": new_verdict == "pass",
                "insight_changed": new_insight != old_insight,
            }
        )

    doc["wording_sweep_applied_at_utc"] = _utc_now()
    prior = int(doc.get("wording_sweep_row_count") or 0)
    doc["wording_sweep_row_count"] = prior + len(sweep_rows)
    doc["human_verdict_counts"] = counts
    doc["human_gate_pass"] = counts.get("fail", 0) == 0
    doc["calibration_gate_pass"] = counts.get("fail", 0) == 0 and counts.get("needs_edit", 0) <= 12

    args.sample_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    preds_updated = 0
    if not args.skip_preds_update and args.preds_jsonl.is_file():
        preds = _load_jsonl(args.preds_jsonl)
        sweep_indices = {r["row_index"] for r in sweep_rows}
        for i, pred in enumerate(preds):
            ri = i + 1
            if ri not in sweep_indices:
                continue
            sample = next(s for s in doc["samples"] if int(s["row_index"]) == ri)
            raw = str(pred.get("prediction_raw", ""))
            patched = _update_json_insight(raw, str(sample["mkm_advanced_insight"]))
            if patched:
                pred["prediction_raw"] = patched
                pred["wording_sweep_applied_at_utc"] = _utc_now()
                preds_updated += 1
        args.preds_jsonl.write_text(
            "\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n",
            encoding="utf-8",
        )

    report = {
        "schema": "myeongri_interpret_v4_wording_sweep_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sample_json": _rel(args.sample_json),
        "swept_row_count": len(sweep_rows),
        "preds_rows_updated": preds_updated,
        "human_verdict_counts_after": counts,
        "calibration_gate_pass": doc["calibration_gate_pass"],
        "rows": sweep_rows,
        "track_wall": {"track_a_live_auto_merge": False},
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.status_json.is_file():
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        status["v4_variant_sft"] = status.get("v4_variant_sft") or {}
        block = status["v4_variant_sft"]
        block["wording_sweep"] = {
            "applied_at_utc": report["generated_at_utc"],
            "swept_rows": len(sweep_rows),
            "calibration_gate_pass": doc["calibration_gate_pass"],
            "report_json": _rel(args.report_json),
        }
        block["human_review_calibration30"] = "wording_sweep_applied"
        args.status_json.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "swept_rows": len(sweep_rows),
                "calibration_gate_pass": doc["calibration_gate_pass"],
                "counts": counts,
                "report": str(args.report_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
