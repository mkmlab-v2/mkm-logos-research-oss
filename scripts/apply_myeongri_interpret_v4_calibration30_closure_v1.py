#!/usr/bin/env python3
"""Close interpret v4 Phase-2 calibration30 human review (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_STATUS = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
DEFAULT_SWEEP = ROOT / "reports/myeongri_interpret_v4_wording_sweep_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_interpret_v4_calibration30_closure_latest.json"
DEFAULT_RADAR = ROOT / "reports/mkm_evolution_radar_daily_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mark_radar_approved(radar_path: Path, candidate_id: str, note: str) -> None:
    if not radar_path.is_file():
        return
    doc = json.loads(radar_path.read_text(encoding="utf-8-sig"))
    for c in doc.get("candidates") or []:
        if str(c.get("id")) == candidate_id:
            c["approval_status"] = "approved"
            c["approved_at_utc"] = _utc_now()
            c["approved_by"] = "commander_chat_2026-06-01"
            if note:
                c["implementation_note"] = note
    doc["generated_at_utc"] = _utc_now()
    radar_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_sample(doc: dict) -> list[str]:
    errors: list[str] = []
    counts = doc.get("human_verdict_counts") or {}
    if int(counts.get("fail", 0)) != 0:
        errors.append("human_verdict_counts.fail must be 0")
    if int(counts.get("needs_edit", 0)) != 0:
        errors.append("human_verdict_counts.needs_edit must be 0")
    if int(counts.get("pass", 0)) != int(doc.get("sample_n") or 30):
        errors.append("all samples must be pass")
    if not doc.get("calibration_gate_pass"):
        errors.append("calibration_gate_pass must be true")
    if not doc.get("wording_sweep_applied_at_utc"):
        errors.append("wording_sweep_applied_at_utc missing")
    for s in doc.get("samples") or []:
        if str(s.get("reviewer_verdict")) != "pass":
            errors.append(f"row {s.get('row_index')} not pass")
            break
    return errors


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample-json", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--status-json", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--radar-json", type=Path, default=DEFAULT_RADAR)
    ap.add_argument("--skip-radar-update", action="store_true")
    args = ap.parse_args()

    if not args.sample_json.is_file():
        print(json.dumps({"ok": False, "error": f"missing {args.sample_json}"}))
        return 2

    doc = json.loads(args.sample_json.read_text(encoding="utf-8"))
    errors = _validate_sample(doc)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False))
        return 1

    now = _utc_now()
    counts = doc["human_verdict_counts"]
    sweep_meta: dict = {}
    if args.sweep_json.is_file():
        sweep_meta = json.loads(args.sweep_json.read_text(encoding="utf-8"))

    doc["calibration30_closure_at_utc"] = now
    doc["calibration30_closure_signed_at_utc"] = now
    doc["commander_signed_at_utc"] = now
    doc["calibration30_closure_source"] = "apply_myeongri_interpret_v4_calibration30_closure_v1.py"

    policy = doc.setdefault("calibration_policy_v1", {})
    policy["phase"] = "calibration30_closed"
    policy["human_verdict_counts"] = counts
    policy["pending_reviewer_verdict_count"] = 0
    policy["calibration_gate_pass"] = True
    policy["wording_sweep_applied_at_utc"] = doc.get("wording_sweep_applied_at_utc")
    policy["wording_sweep_row_count"] = int(
        sweep_meta.get("swept_row_count") or doc.get("wording_sweep_row_count") or 0
    )
    policy["closure_signed_at_utc"] = now
    policy["next_action_ko"] = (
        "Phase2 calibration30 마감(B-track). LoRA 재학습·Track A·실매매 승격은 별도 human gate."
    )

    args.sample_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    closure = {
        "schema": "myeongri_interpret_v4_calibration30_closure_v1",
        "generated_at_utc": now,
        "hypothesis_tier": "B",
        "research_only": True,
        "sample_json": _rel(args.sample_json),
        "prior_signed_sample": policy.get("prior_signed_sample"),
        "human_verdict_counts": counts,
        "calibration_gate_pass": True,
        "wording_sweep_report": _rel(args.sweep_json) if args.sweep_json.is_file() else None,
        "wording_sweep_row_count": policy["wording_sweep_row_count"],
        "phase2_status": "closed",
        "track_wall": {"track_a_live_auto_merge": False, "live_trading_trigger": False},
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.status_json.is_file():
        status = json.loads(args.status_json.read_text(encoding="utf-8"))
        v4 = status.setdefault("v4_variant_sft", {})
        v4["human_review_calibration30"] = {
            "status": "closed",
            "report": _rel(args.sample_json),
            "closure_report": _rel(args.out_json),
            "human_verdict_counts": counts,
            "human_gate_pass": True,
            "calibration_gate_pass": True,
            "wording_sweep_report": closure.get("wording_sweep_report"),
            "wording_sweep_row_count": policy["wording_sweep_row_count"],
            "commander_signed_at_utc": now,
            "calibration30_closure_at_utc": now,
            "interpretation_ko": (
                f"Phase2 calibration30 마감: pass={counts['pass']}/30, "
                f"wording_sweep {policy['wording_sweep_row_count']}행; B-track 연구용."
            ),
        }
        v4["phase2_human_review"] = {
            "status": "closed",
            "phase1_sample_n": 10,
            "phase2_calibration_n": 30,
            "closure_at_utc": now,
        }
        status["generated_at_utc"] = now
        args.status_json.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_radar_update:
        _mark_radar_approved(
            args.radar_json,
            "myeongri_v4_calibration30_closure",
            "Phase2 calibration30 closed; guard448 verify recommended",
        )

    print(
        json.dumps(
            {
                "ok": True,
                "phase2_status": "closed",
                "calibration_gate_pass": True,
                "closure_report": str(args.out_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
