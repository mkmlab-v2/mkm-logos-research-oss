#!/usr/bin/env python3
"""Phase14 full sweep report — aggregates LOGOS-100PCT evidence paths."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_phase14_full_sweep_v1_latest.json"

POINTERS = {
    "closure": ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json",
    "envelope": ROOT / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json",
    "l3_approval": ROOT / "docs/final/artifacts/logos_rag_btrack_promotion_human_approval_v1_latest.json",
    "l3_swap": ROOT / "docs/final/artifacts/logos_rag_l3_production_swap_v1_latest.json",
    "promotion_gate": ROOT / "docs/final/artifacts/logos_rag_btrack_promotion_gate_v1_latest.json",
    "cdim": ROOT / "docs/final/artifacts/logos_cross_domain_interface_latest.json",
    "bridge_registry": ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
    "four_rag_report": ROOT / "docs/final/artifacts/logos_4rag_envelope_refresh_report_v1_latest.json",
    "magic_orb_probe": ROOT / "reports/magic_orb_live_probe_latest.json",
    "showroom_smoke": ROOT / "reports/showroom_trust_viz_public_chain_smoke_latest.json",
    "vps_l3_sync": ROOT / "docs/final/artifacts/logos_rag_l3_vps_sync_v1_latest.json",
}


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    snap: dict[str, object] = {}
    for key, path in POINTERS.items():
        doc = _load(path)
        snap[key] = {
            "present": doc is not None,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "highlights": {},
        }
        if not doc:
            continue
        if key == "closure":
            snap[key]["highlights"] = {"closure_ok": doc.get("closure_ok")}
        elif key == "l3_approval":
            snap[key]["highlights"] = {"decision": doc.get("decision"), "tier": doc.get("tier")}
        elif key == "promotion_gate":
            snap[key]["highlights"] = {
                "action": doc.get("recommended_commander_action"),
                "thematic_hit_at_1": (doc.get("metrics") or {}).get("weak_gold_hit_at_1"),
            }
        elif key == "bridge_registry":
            snap[key]["highlights"] = {
                "bridge_count": doc.get("bridge_count"),
                "human_reviewed_ratio": doc.get("human_reviewed_ratio"),
            }
        elif key == "cdim":
            snap[key]["highlights"] = {"cross_refs": len(doc.get("cross_refs") or [])}
        elif key == "four_rag_report":
            snap[key]["highlights"] = {"rag_4e_all_present": doc.get("rag_4e_all_present")}
        elif key == "magic_orb_probe":
            snap[key]["highlights"] = {"all_ok": all(
                r.get("ok") for r in (doc.get("results") or []) if not r.get("optional")
            )}
        elif key == "showroom_smoke":
            snap[key]["highlights"] = {"ok": doc.get("ok"), "errors_n": len(doc.get("errors") or [])}

    closure_ok = bool((snap.get("closure") or {}).get("highlights", {}).get("closure_ok"))
    doc = {
        "schema": "logos_phase14_full_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "sweep_ok": closure_ok,
        "artifacts": snap,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_trading_trigger": False,
            "corpus_frozen": True,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": closure_ok, "out": str(OUT.relative_to(ROOT)).replace("\\", "/")}, ensure_ascii=False))
    return 0 if closure_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
