#!/usr/bin/env python3
"""Render counsel-prep MD from governed_ai_customization_sales_sheet JSON (internal reports/)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs/final/artifacts/governed_ai_customization_sales_sheet_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/governed_ai_customization_sales_sheet_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render(doc: dict) -> str:
    lines = [
        "# Governed AI Customization — Sales sheet (counsel prep)",
        "",
        f"_Generated: {_utc_now()} · status: {doc.get('status', 'DRAFT')} · "
        f"counsel_required: {doc.get('counsel_required_before_external_send', False)} · "
        f"solo_dev: {bool(doc.get('solo_dev_posture_v1'))}_",
        "",
        "## Headline",
        "",
        doc.get("headline", {}).get("ko", ""),
        "",
        doc.get("headline", {}).get("en", ""),
        "",
        "## Subhead",
        "",
        doc.get("subhead", {}).get("ko", ""),
        "",
        "## Required disclaimers (KO)",
        "",
    ]
    for d in doc.get("required_disclaimers", {}).get("ko") or []:
        lines.append(f"- {d}")
    lines.extend(["", "## Proof artifacts", ""])
    for a in doc.get("proof_artifacts_three") or []:
        lines.append(f"- **{a.get('label')}**: `{a.get('path')}` — {a.get('note', '')}")
    solo = doc.get("solo_dev_posture_v1") or {}
    if solo:
        lines.extend(
            [
                "",
                "## Solo dev (1-person)",
                "",
                solo.get("note_ko", ""),
                "",
                f"Gate: {solo.get('external_send_gate', '')}",
                "",
            ]
        )
    lines.extend(["", "## Forbidden in external deck", ""])
    for f in doc.get("forbidden_in_deck") or []:
        lines.append(f"- {f}")
    lines.extend(
        [
            "",
            "## Next buyer step",
            "",
            doc.get("next_buyer_step", {}).get("ko", ""),
            "",
            f"SSOT JSON: `{doc.get('identity_ref', '')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = json.loads(args.in_json.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_render(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
