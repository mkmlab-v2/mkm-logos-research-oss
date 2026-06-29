#!/usr/bin/env python3
"""Label lexicon↔topology wall divergence exceptions as isolated research cards [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CROSSWALK = ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json"
DEFAULT_AUDIT = ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_cards(
    *,
    crosswalk: dict[str, Any],
    audit: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    audit_rows = {
        str(r.get("prime_en") or ""): r
        for r in ((audit.get("baseline") or {}).get("rows")) or []
        if r.get("prime_en")
    }
    exceptions: list[dict[str, Any]] = []
    for row in crosswalk.get("rows") or []:
        if row.get("wall_status") != "lexicon_only_without_topology":
            continue
        prime = str(row.get("prime_en") or "")
        audit_row = audit_rows.get(prime, {})
        exceptions.append(
            {
                "prime_en": prime,
                "wall_status": row.get("wall_status"),
                "lexicon_hit": row.get("lexicon_hit"),
                "topology_reachable": row.get("topology_reachable"),
                "audit_status": audit_row.get("status") or row.get("audit_status"),
                "hits_sample": audit_row.get("hits_sample") or [],
                "resolution_mode": audit_row.get("resolution_mode"),
                "classification": "structural_exception_isolated",
                "promotion_impact": "none",
                "notes_ko": (
                    "41k lexicon plane hit without 31k verse-atom reachability on probe tokens; "
                    "not repaired in Phase17 — observability label only."
                ),
            }
        )

    wall = crosswalk.get("wall_divergence") or {}
    return {
        "schema": "universal_root_wall_divergence_exception_cards_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "source_crosswalk": "reports/universal_root_topology_crosswalk_v1_latest.json",
        "source_lexicon_audit": "reports/nsm_41k_lexicon_crosswalk_audit_hf_checkpoint_v1_latest.json",
        "topology_spec_pointer": "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
        "summary": {
            "exception_count": len(exceptions),
            "lexicon_only_without_topology_rate": wall.get("lexicon_only_without_topology_rate"),
            "non_control_pairs": (crosswalk.get("summary") or {}).get("non_control_pairs"),
            "plane_separation_preserved": True,
        },
        "forbidden_claims": list(spec.get("forbidden_claims") or [])[:4],
        "exceptions": exceptions,
        "reproduce": "py scripts/build_universal_root_wall_divergence_exception_cards_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    ap.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    crosswalk = _read(args.crosswalk)
    audit = _read(args.audit)
    spec = _read(args.spec)
    if not crosswalk.get("rows"):
        print(json.dumps({"ok": False, "error": "missing_crosswalk_rows"}))
        return 2

    doc = build_cards(crosswalk=crosswalk, audit=audit, spec=spec)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc["summary"]["exception_count"] == int((crosswalk.get("wall_divergence") or {}).get("lexicon_only_without_topology") or 0)
    print(json.dumps({"ok": ok, "exception_count": doc["summary"]["exception_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
