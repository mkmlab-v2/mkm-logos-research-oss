#!/usr/bin/env python3
"""Apply commander human approval for Phase 3 leading sensors (B-track).

Approved scope (default):
  - insight sidecar phase3_leading_sensors_aux (size/confidence only)
  - shield_as_direction_gate remains RETIRED
  - prod btrack_prophecy_score JSON body unchanged
  - Track A / live trading OFF

Does NOT call apply_prophecy_human_approval_v1 or trading execution paths.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final" / "artifacts"
REPORTS = ROOT / "reports"
DEFAULT_APPROVAL_OUT = ART / "btrack_phase3_human_approval_v1_latest.json"
DEFAULT_FEEDS = REPORTS / "btrack_phase3_leading_sensor_feeds_check_v1_latest.json"
DEFAULT_RETIREMENT = REPORTS / "btrack_phase3_shield_role_retirement_pack_v1_latest.json"
DEFAULT_HR_PACK = REPORTS / "btrack_v1_price_only_human_review_pack_v1_latest.json"
DEFAULT_SIDECAR = ART / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_CHAIN = REPORTS / "btrack_phase3_leading_sensors_chain_v1_latest.json"
SIDECAR_SCRIPT = ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
CHAIN_SCRIPT = ROOT / "scripts/run_btrack_phase3_leading_sensors_chain_v1.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    cp = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)


def _preflight(
    *,
    feeds: Path,
    retirement: Path,
    skip_feeds_gate: bool,
) -> dict[str, Any]:
    feeds_doc = _load(feeds)
    retire_doc = _load(retirement)
    if not skip_feeds_gate:
        if not feeds_doc.get("ok"):
            raise SystemExit(f"Feeds check not ok: {feeds}")
        if int(feeds_doc.get("n_measured_sensors") or 0) < int(feeds_doc.get("require_measured") or 2):
            raise SystemExit("Insufficient measured sensors for Phase 3 approval apply.")
    verdict = (retire_doc.get("verdict") or {}) if isinstance(retire_doc.get("verdict"), dict) else {}
    if str(verdict.get("shield_as_direction_gate") or "") != "RETIRED":
        raise SystemExit(
            "shield_as_direction_gate must be RETIRED before apply; re-run sweep/retirement pack."
        )
    return {"feeds": feeds_doc, "retirement": retire_doc}


def _patch_hr_pack(hr_path: Path, approval_ref: str, reviewer: str, note: str) -> None:
    hr = _load(hr_path)
    if not hr:
        return
    decision = hr.setdefault("decision", {})
    if not isinstance(decision, dict):
        return
    decision["human_commander_override"] = "APPROVED_PHASE3_AUX_ONLY"
    decision["phase3_aux_promotion"] = "APPROVED"
    decision["apply_to_prod_score_json"] = False
    decision["track_a_promotion"] = False
    decision["auto_promote"] = False
    decision["human_approved_at_utc"] = _now()
    decision["human_reviewer"] = reviewer
    decision["human_note_ko"] = note
    hr["human_approval_ref"] = approval_ref
    _write_json(hr_path, hr)


def _patch_retirement(retire_path: Path, approval_ref: str, reviewer: str) -> None:
    doc = _load(retire_path)
    if not doc:
        return
    doc["human_approval"] = {
        "decision": "APPROVED",
        "reviewer": reviewer,
        "approved_at_utc": _now(),
        "promotion_scope": "size_confidence_aux_only",
        "artifact_ref": approval_ref,
    }
    verdict = doc.setdefault("verdict", {})
    if isinstance(verdict, dict):
        verdict["human_approved"] = True
        verdict["apply_prod"] = False
        verdict["track_a_promotion"] = "NO"
    _write_json(retire_path, doc)


def _patch_sidecar(sidecar_path: Path, approval_ref: str) -> None:
    doc = _load(sidecar_path)
    if not doc:
        raise SystemExit(f"Missing sidecar after rebuild: {sidecar_path}")
    doc["human_approval_ref"] = approval_ref
    doc["human_approval"] = {
        "schema": "btrack_phase3_human_approval_v1",
        "decision": "APPROVED",
        "scope": "size_confidence_aux_only",
        "shield_as_direction_gate": "RETIRED",
        "prod_score_mutation": False,
        "track_a_promotion": False,
    }
    p3 = doc.get("phase3_merge")
    if isinstance(p3, dict):
        p3["human_approved"] = True
        p3["promotion_scope"] = "size_confidence_aux_only"
    doc["research_only"] = True
    _write_json(sidecar_path, doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument(
        "--note",
        default="지휘관 in-chat 승인: Phase3 size/confidence aux만; shield 방향·prod score·Track A 제외.",
    )
    ap.add_argument("--approval-out", type=Path, default=DEFAULT_APPROVAL_OUT)
    ap.add_argument("--feeds-check", type=Path, default=DEFAULT_FEEDS)
    ap.add_argument("--retirement-pack", type=Path, default=DEFAULT_RETIREMENT)
    ap.add_argument("--hr-pack", type=Path, default=DEFAULT_HR_PACK)
    ap.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--skip-feeds-gate", action="store_true")
    ap.add_argument("--skip-chain-rerun", action="store_true")
    ap.add_argument("--skip-sidecar-rebuild", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ctx = _preflight(
        feeds=args.feeds_check,
        retirement=args.retirement_pack,
        skip_feeds_gate=args.skip_feeds_gate,
    )

    approval_ref = str(args.approval_out.relative_to(ROOT)).replace("\\", "/")
    payload: dict[str, Any] = {
        "schema": "btrack_phase3_human_approval_v1",
        "recorded_at_utc": _now(),
        "reviewer": args.reviewer,
        "decision": "APPROVED",
        "scope": {
            "phase3_aux_sidecar": True,
            "shield_direction_gate": False,
            "prod_score_json_mutation": False,
            "track_a_promotion": False,
            "live_trading": False,
        },
        "note": args.note,
        "evidence": {
            "feeds_check": str(args.feeds_check.resolve()),
            "shield_retirement": str(args.retirement_pack.resolve()),
            "chain_latest": str(DEFAULT_CHAIN.resolve()),
            "hr_pack": str(args.hr_pack.resolve()) if args.hr_pack.is_file() else None,
        },
        "preflight_snapshot": {
            "feeds_ok": ctx["feeds"].get("ok"),
            "n_measured_sensors": ctx["feeds"].get("n_measured_sensors"),
            "shield_status": (ctx["retirement"].get("verdict") or {}).get("shield_as_direction_gate"),
        },
        "track_wall": {
            "source_track": "B",
            "research_only_sidecar": True,
            "btrack_to_a_auto_bridge": False,
        },
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "approval": payload}, ensure_ascii=False, indent=2))
        return 0

    _write_json(args.approval_out, payload)
    print(f"WROTE: {args.approval_out.resolve()}")

    py = sys.executable
    if not args.skip_chain_rerun and CHAIN_SCRIPT.is_file():
        _run(
            [
                py,
                str(CHAIN_SCRIPT),
                "--fetch-binance",
                "--join-180",
                "--skip-auto-optimal",
                "--skip-seed",
            ]
        )

    if not args.skip_sidecar_rebuild and SIDECAR_SCRIPT.is_file():
        _run([py, str(SIDECAR_SCRIPT)])

    _patch_hr_pack(args.hr_pack, approval_ref, args.reviewer, args.note)
    if args.hr_pack.is_file():
        print(f"PATCHED: {args.hr_pack.resolve()}")

    _patch_retirement(args.retirement_pack, approval_ref, args.reviewer)
    if args.retirement_pack.is_file():
        print(f"PATCHED: {args.retirement_pack.resolve()}")

    _patch_sidecar(args.sidecar, approval_ref)
    print(f"PATCHED: {args.sidecar.resolve()}")

    ld = ROOT / "scripts/log_agent_decision.py"
    if ld.is_file():
        subprocess.run(
            [
                py,
                str(ld),
                "--mission-id",
                "btrack_phase3_human_approval",
                "--stage",
                "applied",
                "--decision",
                "APPROVED_PHASE3_AUX_ONLY",
                "--evidence-path",
                str(args.approval_out.resolve()),
                "--actor",
                args.reviewer,
                "--note",
                args.note[:200],
            ],
            cwd=str(ROOT),
            check=False,
        )

    print("OK Phase3 human approval applied (aux sidecar only; prod score & Track A unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
