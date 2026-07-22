#!/usr/bin/env python3
"""Weather→main general_prophecy merge readiness/signoff gate (B-track, default HOLD).

Mirrors biblical_history holdout signoff pattern. Does NOT merge.
Defaults merge_decision=HOLD; full calibration-lab n=360 dump stays blocked.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNOFF = ROOT / "docs/final/artifacts/weather_to_general_prophecy_merge_signoff_v1.json"
DEFAULT_WEATHER = ROOT / "docs/final/artifacts/weather_prophecy_triplet_latest.json"
DEFAULT_MAIN = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/weather_to_general_prophecy_merge_signoff_gate_v1_latest.json"
DEFAULT_REPORT = ROOT / "reports/weather_to_general_prophecy_merge_readiness_v1_latest.json"

CALIBRATION_TAGS = frozenset(
    {
        "weather_calibration_v1",
        "walkforward_hist",
        "triplet_shared_target",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _qids(doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for q in doc.get("questions") or []:
        if isinstance(q, dict) and isinstance(q.get("question_id"), str):
            out.add(q["question_id"])
    return out


def _is_calibration_lab(q: dict[str, Any]) -> bool:
    tags = {str(t).lower() for t in (q.get("domain_tags") or [])}
    return bool(tags & {t.lower() for t in CALIBRATION_TAGS})


def _class_b_scorable(q: dict[str, Any], allowlist: set[str]) -> bool:
    qid = str(q.get("question_id") or "")
    if allowlist and qid in allowlist:
        return True
    tags = {str(t).lower() for t in (q.get("domain_tags") or [])}
    if "class_b_scorable_v1" in tags:
        return True
    # Controlled subset: forward ops weather only — never calibration lab.
    if _is_calibration_lab(q):
        return False
    return "weather" in tags


def evaluate(
    *,
    signoff: dict[str, Any],
    weather: dict[str, Any],
    main: dict[str, Any],
) -> dict[str, Any]:
    weather_qs = [q for q in (weather.get("questions") or []) if isinstance(q, dict)]
    main_ids = _qids(main)
    weather_ids = _qids(weather)
    allowlist = {
        str(x)
        for x in (signoff.get("allowlist_question_ids") or [])
        if isinstance(x, str) and x.strip()
    }

    cal_n = sum(1 for q in weather_qs if _is_calibration_lab(q))
    class_b = [
        str(q.get("question_id"))
        for q in weather_qs
        if _class_b_scorable(q, allowlist) and str(q.get("question_id") or "") not in main_ids
    ]
    would_add_full = sorted(weather_ids - main_ids)

    approved = bool(signoff.get("approved"))
    allow_full = bool(signoff.get("allow_full_calibration_lab_merge"))
    mode = str(signoff.get("merge_mode") or "class_b_scorable_subset_only")

    reasons: list[str] = []
    merge_decision = "HOLD"
    merge_allowed = False

    if not approved:
        reasons.append("signoff.approved=false (default HOLD)")
    if cal_n > 0 and not allow_full:
        reasons.append(
            f"weather sidecar has {cal_n} calibration-lab questions "
            f"(tags {sorted(CALIBRATION_TAGS)}); full dump blocked unless "
            "allow_full_calibration_lab_merge=true"
        )
    if mode == "class_b_scorable_subset_only" and not class_b:
        reasons.append(
            "class_b_scorable_subset empty (no non-calibration weather candidates / empty allowlist)"
        )

    if approved and mode == "class_b_scorable_subset_only" and class_b:
        merge_decision = "READY_CLASS_B_SUBSET"
        merge_allowed = True
        reasons.append(f"approved + {len(class_b)} Class-B scorable id(s) not yet in main")
    elif approved and allow_full and mode in {"full_calibration_lab", "allow_full"}:
        merge_decision = "READY_FULL_CALIBRATION_EXPLICIT"
        merge_allowed = True
        reasons.append("approved + allow_full_calibration_lab_merge — commander-explicit only")
    elif approved and not merge_allowed:
        merge_decision = "HOLD"
        reasons.append("approved but no safe subset / full-merge flag — still HOLD")

    dry_run_cmds = [
        "py scripts/check_weather_to_general_prophecy_merge_signoff_gate_v1.py",
        "py scripts/merge_weather_to_general_prophecy_v1.py --dry-run",
    ]
    apply_cmds = [
        "py scripts/merge_weather_to_general_prophecy_v1.py --apply",
        "py scripts/eval_general_prophecy_brier_score.py",
    ]

    return {
        "schema": "weather_to_general_prophecy_merge_signoff_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "ok": True,
        "merge_decision": merge_decision,
        "merge_allowed": merge_allowed,
        "merge_applied": False,
        "dry_run_only": True,
        "signoff": {
            "path": str(DEFAULT_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "approved": approved,
            "merge_mode": mode,
            "allow_full_calibration_lab_merge": allow_full,
            "allowlist_question_ids": sorted(allowlist),
        },
        "counts": {
            "weather_sidecar_questions": len(weather_ids),
            "weather_calibration_lab_questions": cal_n,
            "main_questions": len(main_ids),
            "would_add_if_full_merge": len(would_add_full),
            "class_b_scorable_not_in_main": len(class_b),
        },
        "class_b_scorable_question_ids": class_b[:50],
        "class_b_scorable_truncated": len(class_b) > 50,
        "rationale": reasons,
        "unblock_path": [
            "1) Keep weather sidecar separate for calibration Brier (default).",
            "2) For controlled Class-B subset: set signoff.approved=true, "
            "fill allowlist_question_ids OR tag questions class_b_scorable_v1 "
            "(non-calibration only), then dry-run merge script.",
            "3) Full n=360 calibration merge: commander must set approved=true AND "
            "allow_full_calibration_lab_merge=true AND merge_mode=full_calibration_lab "
            "(explicit contamination acceptance).",
            "4) Generic overdue main-GP items remain manual via "
            "resolve_general_prophecy_question_v1.py — not this gate.",
        ],
        "next_commands": {
            "gate_refresh": dry_run_cmds[0],
            "merge_dry_run": dry_run_cmds[1],
            "merge_apply_only_if_gate_ready": apply_cmds,
        },
        "inputs": {
            "signoff": str(DEFAULT_SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "weather_sidecar": str(DEFAULT_WEATHER.relative_to(ROOT)).replace("\\", "/"),
            "main_registry": str(DEFAULT_MAIN.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--weather-json", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_MAIN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    missing = [p for p in (args.signoff_json, args.weather_json, args.registry_json) if not p.is_file()]
    if missing:
        print(json.dumps({"ok": False, "missing": [str(p) for p in missing]}, ensure_ascii=False), file=sys.stderr)
        return 2

    doc = evaluate(
        signoff=_load(args.signoff_json),
        weather=_load(args.weather_json),
        main=_load(args.registry_json),
    )

    # Mirror readiness report (ops path used by prior Option A note).
    readiness = {
        "schema": "weather_to_general_prophecy_merge_readiness_v1",
        "generated_at_utc": doc["generated_at_utc"],
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_to_a_track_allowed": False,
        "merge_decision": doc["merge_decision"],
        "merge_applied": False,
        "dry_run_only": True,
        "gate_script": "scripts/check_weather_to_general_prophecy_merge_signoff_gate_v1.py",
        "signoff_json": doc["inputs"]["signoff"],
        "merge_script": "scripts/merge_weather_to_general_prophecy_v1.py",
        "rationale": doc["rationale"],
        "counts": doc["counts"],
        "what_would_be_needed_to_unblock": doc["unblock_path"],
        "ok": True,
    }

    for path, payload in ((args.out_json, doc), (args.report_json, readiness)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "merge_decision": doc["merge_decision"],
                "merge_allowed": doc["merge_allowed"],
                "class_b_scorable_not_in_main": doc["counts"]["class_b_scorable_not_in_main"],
                "would_add_if_full_merge": doc["counts"]["would_add_if_full_merge"],
                "out": str(args.out_json),
                "readiness": str(args.report_json),
            },
            ensure_ascii=False,
        )
    )
    # Exit 0 always when gate evaluated; HOLD is a successful evaluation.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
