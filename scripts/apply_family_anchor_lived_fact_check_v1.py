#!/usr/bin/env python3
"""Merge family_anchor fact-check session responses into lived calibration JSON."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SESSION = ROOT / "docs/final/artifacts/family_anchor_fact_check_session_daughter_v1_latest.json"
DEFAULT_ANCHOR = ROOT / "docs/final/artifacts/family_anchor_lived_calibration_our_daughter_v1_latest.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/daughter_2026_integrated_guide_v4_minimal_latest.json"
DEFAULT_REPORT = ROOT / "reports/family_anchor_fact_check_apply_latest.json"

NARRATIVE_PATCHES: dict[str, dict[str, list[str]]] = {
    "wealth_pocket_money": {
        "high": ["wealth_comparison_stress_lived_high"],
        "neutral": ["wealth_comparison_stress_lived_neutral"],
        "low": ["wealth_comparison_stress_lived_low"],
    },
    "romance_peer": {
        "high": ["romance_peer_affinity_lived_present"],
        "neutral": ["romance_peer_affinity_lived_neutral"],
        "low": ["romance_peer_affinity_lived_low"],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _axis_map(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in session.get("axes") or []:
        if isinstance(row, dict) and row.get("axis"):
            out[str(row["axis"])] = row
    return out


def _responses_complete(axis_row: dict[str, Any]) -> bool:
    resp = axis_row.get("responses")
    if not isinstance(resp, dict) or not resp:
        return False
    return all(v is not None and str(v).strip() for v in resp.values())


def _patch_preferred(anchor: dict[str, Any], axis: str, stress_key: str, value: str) -> None:
    val = str(value).strip().lower()
    bucket = "neutral"
    if val in ("high", "often", "yes", "많음", "자주"):
        bucket = "high"
    elif val in ("low", "rarely", "no", "없음", "거의 없음"):
        bucket = "low"
    patches = NARRATIVE_PATCHES.get(axis, {}).get(bucket, [])
    pref = anchor.setdefault("preferred_narrative", [])
    for p in patches:
        if p not in pref:
            pref.append(p)


def apply_session(
    session: dict[str, Any],
    anchor: dict[str, Any],
    *,
    allow_partial: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    axis_by_name = _axis_map(session)
    supp = anchor.get("supplementary_axes")
    if not isinstance(supp, list):
        raise SystemExit("anchor missing supplementary_axes[]")

    for block in supp:
        if not isinstance(block, dict):
            continue
        axis_name = str(block.get("axis") or "")
        sess = axis_by_name.get(axis_name)
        if not sess:
            warnings.append(f"session missing axis {axis_name}")
            continue
        if not _responses_complete(sess) and not allow_partial:
            raise SystemExit(f"incomplete responses for axis {axis_name}")
        block["responses"] = dict(sess.get("responses") or {})
        block["responses"]["lived_check_status"] = (
            "completed" if _responses_complete(sess) else "partial"
        )
        block["status"] = "lived_check_applied"
        for k, v in block["responses"].items():
            if k != "lived_check_status" and v:
                _patch_preferred(anchor, axis_name, k, str(v))

    anchor["ts_utc"] = _now()
    resp_root = anchor.setdefault("responses", {})
    if isinstance(resp_root, dict):
        resp_root["lived_fact_check_applied_at"] = _now()
        if session.get("operator_v4_helpful") is True:
            resp_root["operator_verdict_v4_helpful"] = "v4_minimal_matches_after_fact_check"
        elif session.get("operator_v4_helpful") is False:
            resp_root["operator_verdict_v4_helpful"] = "v4_minimal_needs_revision"

    session["status"] = "applied" if not allow_partial else "ready_to_apply"
    return anchor, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply family anchor lived fact-check session.")
    ap.add_argument("--session-json", type=Path, default=DEFAULT_SESSION)
    ap.add_argument("--anchor-json", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--v4-json", type=Path, default=DEFAULT_V4)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--v4-helpful", choices=("true", "false"), default=None)
    args = ap.parse_args()

    session_path = args.session_json if args.session_json.is_absolute() else ROOT / args.session_json
    anchor_path = args.anchor_json if args.anchor_json.is_absolute() else ROOT / args.anchor_json
    v4_path = args.v4_json if args.v4_json.is_absolute() else ROOT / args.v4_json
    report_path = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json

    session = _read(session_path)
    anchor = _read(anchor_path)
    if session.get("anchor_id") != anchor.get("anchor_id"):
        raise SystemExit("anchor_id mismatch between session and anchor")

    if args.v4_helpful == "true":
        session["operator_v4_helpful"] = True
    elif args.v4_helpful == "false":
        session["operator_v4_helpful"] = False

    updated_anchor, warnings = apply_session(session, anchor, allow_partial=args.allow_partial)

    v4_note: dict[str, Any] | None = None
    if v4_path.is_file():
        v4 = _read(v4_path)
        try:
            session_ref = str(session_path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            session_ref = str(session_path)
        v4_note = {
            "fact_check_applied_at_utc": _now(),
            "session_ref": session_ref,
            "operator_v4_helpful": session.get("operator_v4_helpful"),
        }
        v4["fact_check_apply"] = v4_note

    report = {
        "schema": "family_anchor_fact_check_apply_report_v1",
        "applied_at_utc": _now(),
        "dry_run": args.dry_run,
        "session_path": str(session_path),
        "anchor_path": str(anchor_path),
        "warnings": warnings,
        "axes_applied": [a.get("axis") for a in (session.get("axes") or []) if isinstance(a, dict)],
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    _write(session_path, session)
    _write(anchor_path, updated_anchor)
    if v4_note is not None:
        _write(v4_path, v4)
    _write(report_path, report)
    print(f"applied -> {anchor_path}")
    print(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
