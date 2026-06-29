#!/usr/bin/env python3
"""[HYPO] Record commander accept/reject for DE/NIM LUT staging rows (no codec wire)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
PICKLIST = ROOT / "reports/nvidia_de_nim_commander_anchor_picklist_v1_latest.json"
OUT = ROOT / "reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_decisions(rows: list[dict]) -> dict[str, str]:
    """Accept rows with substantive verse refs; reject placeholder-only."""
    out: dict[str, str] = {}
    for r in rows:
        pid = str(r.get("probe_id") or "")
        refs = [str(x) for x in (r.get("verse_refs") or [])]
        bad = not refs or all(
            "no specific verse" in x.lower() or x.lower() in {"logos", "tariff", "semiconductor"}
            for x in refs
        )
        if pid.startswith("concept:concept:tariff") or (
            pid.startswith("concept:") and bad
        ):
            out[pid] = "reject"
        elif bad:
            out[pid] = "reject"
        else:
            out[pid] = "accept"
    return out


def _apply_lut(lut: dict[str, Any], decisions: dict[str, str], signoff_by: str) -> None:
    staging = lut.get("nim_anchor_staging_v1") or {}
    by_probe = staging.get("candidates_by_probe_id") or {}
    for pid, decision in decisions.items():
        row = by_probe.get(pid)
        if not isinstance(row, dict):
            continue
        row["candidate_anchor_status"] = (
            "commander_accepted_staging_v1"
            if decision == "accept"
            else "commander_rejected_staging_v1"
        )
        row["commander_signoff_utc"] = _utc()
        row["commander_signoff_by"] = signoff_by
    de_staging = lut.get("de_probe_staging_v1") or {}
    de_by = de_staging.get("candidates_by_probe_id") or {}
    for pid, decision in decisions.items():
        row = de_by.get(pid)
        if isinstance(row, dict):
            row["candidate_anchor_status"] = (
                "commander_accepted_staging_v1"
                if decision == "accept"
                else "commander_rejected_staging_v1"
            )
    lut["de_nim_commander_anchor_signoff_v1"] = {
        "signoff_utc": _utc(),
        "signoff_by": signoff_by,
        "decisions": decisions,
        "codec_wired": False,
        "track_a_active_write": False,
    }


def apply_signoff_from_file(signoff_path: Path) -> int:
    if not signoff_path.is_file() or not LUT.is_file():
        return 2
    doc = json.loads(signoff_path.read_text(encoding="utf-8-sig"))
    decisions = {
        pid: "accept"
        for pid in doc.get("accepted_probe_ids") or []
    }
    for pid in doc.get("rejected_probe_ids") or []:
        decisions[str(pid)] = "reject"
    lut = json.loads(LUT.read_text(encoding="utf-8-sig"))
    _apply_lut(lut, decisions, str(doc.get("signoff_by") or "commander"))
    LUT.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-by", default="commander")
    ap.add_argument(
        "--accept-all",
        action="store_true",
        help="Accept every picklist row (staging only)",
    )
    ap.add_argument(
        "--decisions-json",
        type=Path,
        default=None,
        help='JSON object probe_id -> accept|reject',
    )
    ap.add_argument(
        "--reapply-latest",
        action="store_true",
        help="Re-apply reports/nvidia_de_nim_commander_anchor_signoff_v1_latest.json to LUT",
    )
    args = ap.parse_args()

    if args.reapply_latest:
        return apply_signoff_from_file(OUT)

    pick = json.loads(PICKLIST.read_text(encoding="utf-8-sig")) if PICKLIST.is_file() else {}
    rows = pick.get("rows") or []
    if args.decisions_json and args.decisions_json.is_file():
        decisions = json.loads(args.decisions_json.read_text(encoding="utf-8-sig"))
    elif args.accept_all:
        decisions = {str(r["probe_id"]): "accept" for r in rows if r.get("probe_id")}
    else:
        decisions = _default_decisions(rows)

    if not LUT.is_file():
        print(json.dumps({"error": "missing_lut"}))
        return 2
    lut = json.loads(LUT.read_text(encoding="utf-8-sig"))
    _apply_lut(lut, decisions, args.signoff_by)
    LUT.write_text(json.dumps(lut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    accepted = [k for k, v in decisions.items() if v == "accept"]
    rejected = [k for k, v in decisions.items() if v == "reject"]
    doc = {
        "schema": "nvidia_de_nim_commander_anchor_signoff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "signoff_by": args.signoff_by,
        "accepted_probe_ids": accepted,
        "rejected_probe_ids": rejected,
        "codec_wired": False,
        "track_a_active_write": False,
        "next": "lut_codec_staging_review_manual_only",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"wrote": str(OUT), "accepted": len(accepted), "rejected": len(rejected)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
