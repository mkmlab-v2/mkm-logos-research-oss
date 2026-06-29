#!/usr/bin/env python3
"""Record commander sign-off for Logos OL bridge deck PDF pack (B-track · does not enable Track A)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
PDF_MANIFEST = ROOT / "reports/logos_ops_deck/logos_ol_bridge_deck_pdf_export_v1_latest.json"
DEFAULT_OUT = ART / "logos_ol_bridge_deck_commander_signoff_v1_latest.json"

VALID_SCOPES = frozenset(
    {
        "internal_rehearsal_complete",
        "counsel_submission",
        "external_send",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(*, reference: str, scope: str, notes: str) -> dict[str, Any]:
    ref = reference.strip()
    if not ref:
        raise ValueError("reference required")
    if scope not in VALID_SCOPES:
        raise ValueError(f"scope must be one of {sorted(VALID_SCOPES)}")

    pdf_exports: list[dict[str, Any]] = []
    if PDF_MANIFEST.is_file():
        manifest = json.loads(PDF_MANIFEST.read_text(encoding="utf-8-sig"))
        pdf_exports = [e for e in (manifest.get("exports") or []) if isinstance(e, dict)]

    return {
        "schema": "logos_ol_bridge_deck_commander_signoff_v1",
        "recorded_at_utc": _utc_now(),
        "commander_reference": ref,
        "scope": scope,
        "notes": (notes or "").strip() or None,
        "status": "COMMANDER_SIGNED",
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "send_gate": "HOLD" if scope != "external_send" else "OPEN",
        "ready_for_external_send": scope == "external_send",
        "pdf_manifest": str(PDF_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "pdf_exports": pdf_exports,
        "boundary_ack": (
            "Deck sign-off records commander review of internal B-track artifacts only. "
            "scope=internal_rehearsal_complete does not authorize Track A, live trading, or prophecy claims. "
            "external_send requires counsel + PUBLIC_FACING checklist."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reference", required=True)
    ap.add_argument(
        "--scope",
        default="internal_rehearsal_complete",
        choices=sorted(VALID_SCOPES),
    )
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    doc = build(reference=args.reference, scope=args.scope, notes=args.notes)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if PDF_MANIFEST.is_file():
        manifest = json.loads(PDF_MANIFEST.read_text(encoding="utf-8-sig"))
        manifest["human_signoff_required"] = False
        manifest["commander_signoff_recorded"] = True
        manifest["commander_signoff_scope"] = doc["scope"]
        manifest["commander_signoff_at_utc"] = doc["recorded_at_utc"]
        PDF_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    closure = ROOT / "reports/logos_ol_graph_bridge_post_phase3_closure_v1_latest.json"
    if closure.is_file():
        cdoc = json.loads(closure.read_text(encoding="utf-8-sig"))
        cdoc["human_signoff_required"] = False
        cdoc["commander_signoff_recorded"] = True
        cdoc["commander_signoff_scope"] = doc["scope"]
        closure.write_text(json.dumps(cdoc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "scope": doc["scope"],
                "send_gate": doc["send_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
