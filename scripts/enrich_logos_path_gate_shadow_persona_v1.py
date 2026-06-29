#!/usr/bin/env python3
"""Attach key-verse shadow persona hints to path gate checks [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE_DEFAULT = ROOT / "reports/logos_path_verification_gate_v1_latest.json"
SHADOW_DEFAULT = ROOT / "reports/verse_metadata_shadow_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_vid(vid: str) -> str:
    v = (vid or "").strip()
    if v.lower().startswith("john."):
        return "Jhn." + v.split(".", 1)[1]
    return v


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build(*, gate_doc: dict[str, Any], shadow_doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(gate_doc)
    rows = shadow_doc.get("rows") or []
    by_vid = {_normalize_vid(str(r.get("verse_id") or "")): r for r in rows}

    checks = out.get("checks") or []
    hinted = 0
    for chk in checks:
        hints = []
        for c in (chk.get("citations") or []):
            r = by_vid.get(_normalize_vid(str(c)))
            if not r:
                continue
            hints.append(
                {
                    "verse_id": r.get("verse_id"),
                    "primary_tag": r.get("primary_tag"),
                    "confidence": r.get("confidence"),
                    "tag_distribution": r.get("tag_distribution"),
                }
            )
        if hints:
            chk["shadow_persona_hint"] = hints
            hinted += 1

    out["checks"] = checks
    summary = dict(out.get("summary") or {})
    summary["shadow_persona_hint_units"] = hinted
    summary["shadow_persona_non_gating"] = True
    summary["gate_pass"] = summary.get("gate_pass")
    out["summary"] = summary
    out["shadow_persona_meta"] = {
        "schema": "path_gate_shadow_persona_hint_v1",
        "enriched_at_utc": _utc(),
        "source_shadow": "reports/verse_metadata_shadow_v1_latest.json",
        "non_gating": True,
        "research_only": True,
        "does_not_affect_gate_pass": True,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", type=Path, default=GATE_DEFAULT)
    ap.add_argument("--shadow", type=Path, default=SHADOW_DEFAULT)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    gate_doc = _load(args.gate)
    shadow_doc = _load(args.shadow)
    if not gate_doc:
        print(json.dumps({"ok": False, "error": "path gate missing"}))
        return 2
    if not shadow_doc:
        print(json.dumps({"ok": False, "error": "shadow metadata missing"}))
        return 2

    out_path = args.out or args.gate
    enriched = build(gate_doc=gate_doc, shadow_doc=shadow_doc)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "shadow_persona_hint_units": (enriched.get("summary") or {}).get("shadow_persona_hint_units"),
                "gate_pass_unchanged": (enriched.get("summary") or {}).get("gate_pass"),
                "out": str(out_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
