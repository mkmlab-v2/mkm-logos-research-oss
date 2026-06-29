#!/usr/bin/env python3
"""Enforce Universal Root GTM FREEZE — PUBLIC_GTM_ALLOWED gate [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_gtm_freeze_lib_v1 import evaluate_gtm_freeze  # noqa: E402

OUT = ROOT / "reports/universal_root_gtm_freeze_check_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"


def _patch_gtm_milestone() -> None:
    if not GTM.is_file():
        return
    doc = json.loads(GTM.read_text(encoding="utf-8-sig"))
    ev = evaluate_gtm_freeze(action="read_only")
    if not ev.get("active"):
        return
    milestones = doc.setdefault("milestones", {})
    ur = milestones.setdefault("UR-W1", {})
    if int(ev.get("external_repro_count") or 0) < 1:
        ur["status"] = "gtm_frozen"
        ur["note"] = (
            "GTM FREEZE: external repro=0; no maintainer bumps; Phase-1A integrity required. "
            "Reddit/X posted 2026-06-21 (historical)."
        )
    doc["gtm_freeze"] = {
        **(doc.get("gtm_freeze") or {}),
        "active": True,
        "public_gtm_allowed": bool(ev.get("public_gtm_allowed")),
        "integrity_ok": bool(ev.get("integrity_ok")),
        "last_check_utc": ev.get("evaluated_at_utc"),
        "freeze_ssot": "docs/final/artifacts/universal_root_gtm_freeze_v1_latest.json",
    }
    doc["updated_at_utc"] = ev.get("evaluated_at_utc")
    GTM.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 unless public_gtm_allowed (integrity AND external_repro master key)",
    )
    ap.add_argument(
        "--strict-integrity",
        action="store_true",
        help="exit 1 on Phase1A integrity violations only (external_repro=0 may still exit 0)",
    )
    ap.add_argument("--action", default="read_only", help="maintainer_bump | discussions_live_post | read_only")
    ap.add_argument("--commander-override-freeze", action="store_true")
    ap.add_argument("--patch-gtm", action="store_true", help="sync UR-W1 status + freeze block on GTM SSOT")
    ap.add_argument("--skip-integrity", action="store_true", help="skip Phase1A integrity sub-gates")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if args.patch_gtm:
        _patch_gtm_milestone()

    ev = evaluate_gtm_freeze(
        action=args.action,
        commander_override=args.commander_override_freeze,
        skip_integrity=args.skip_integrity,
    )

    doc = {
        **ev,
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": "py scripts/check_universal_root_gtm_freeze_v1.py --strict-integrity --patch-gtm",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ev["ok"],
                "integrity_ok": ev.get("integrity_ok"),
                "public_gtm_allowed": ev["public_gtm_allowed"],
                "hold_reasons": ev.get("hold_reasons"),
                "out": str(args.out),
            }
        )
    )

    if args.strict_integrity and not ev.get("integrity_ok"):
        return 1
    if args.strict and not ev.get("public_gtm_allowed"):
        return 1
    if args.strict and not ev.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
