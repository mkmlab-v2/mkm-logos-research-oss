#!/usr/bin/env python3
"""B-track Sasang vs pseudo-4D mismatch gate + ops handoff validation [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_sasang_role_router_v1 import (  # noqa: E402
    SASANG_ROLES,
    build_ops_registry_doc,
    validate_ops_handoff_chain,
)

OUT_DEFAULT = ROOT / "reports/btrack_sasang_role_mismatch_gate_v1_latest.json"
SHADOW_DEFAULT = ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build(shadow_path: Path, *, max_mismatch_rate: float) -> dict[str, Any]:
    shadow = _load(shadow_path)
    entries = shadow.get("entries") or []
    mismatch_rate = float((shadow.get("mismatch_summary") or {}).get("mismatch_rate") or 0.0)
    role_counts = shadow.get("role_counts") or {}
    all_roles_present = all(int(role_counts.get(r, 0) or 0) > 0 for r in SASANG_ROLES)

    ops = build_ops_registry_doc()
    demo_chain = ["taeyang", "soyang", "soeumin", "taeeum"]
    handoff = validate_ops_handoff_chain(demo_chain)
    bad_handoff = validate_ops_handoff_chain(["soeumin", "taeyang"])

    gate_pass = (
        shadow.get("codebook_unmodified") is True
        and shadow.get("track_a_bridge") is False
        and len(entries) >= 1000
        and all_roles_present
        and mismatch_rate <= max_mismatch_rate
        and handoff.get("ok") is True
        and bad_handoff.get("ok") is False
    )

    return {
        "schema": "btrack_sasang_role_mismatch_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "track_a_bridge": False,
        "shadow_path": str(shadow_path.resolve()),
        "summary": {
            "gate_pass": gate_pass,
            "mismatch_rate": mismatch_rate,
            "max_mismatch_rate": max_mismatch_rate,
            "all_roles_present": all_roles_present,
            "codebook_unmodified": shadow.get("codebook_unmodified"),
            "lexicon_entries": len(entries),
            "class_mismatch_escalation_sample": (shadow.get("mismatch_sample") or [])[:8],
        },
        "ops_registry": ops,
        "handoff_validation": {
            "valid_demo_chain": handoff,
            "invalid_chain_blocked": bad_handoff,
        },
        "reproduce_cmd": "py scripts/build_btrack_sasang_role_mismatch_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shadow", type=Path, default=SHADOW_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-mismatch-rate", type=float, default=0.75)
    args = ap.parse_args()

    doc = build(args.shadow, max_mismatch_rate=args.max_mismatch_rate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["summary"]["gate_pass"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if doc["summary"]["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
