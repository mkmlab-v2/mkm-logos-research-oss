#!/usr/bin/env python3
"""Validate bidirectional WORLDVIEW §5 ↔ 75-formula SSOT cross-links ([HYPO] bridge)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORLDVIEW = ROOT / "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md"
ASCII_POINTER = ROOT / "docs/final/MKM12_75_FORMULAS_SSOT_V1.md"
FORMULAS = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
PROMOTION = ROOT / "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json"
CANON = ROOT / "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md"
OUT = ROOT / "docs/final/artifacts/worldview_formula_crosslink_bridge_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    checks: list[dict[str, object]] = []

    wv_ok = WORLDVIEW.is_file()
    wv_text = _read(WORLDVIEW) if wv_ok else ""
    checks.append(
        {
            "name": "worldview_file",
            "ok": wv_ok,
            "path": str(WORLDVIEW.relative_to(ROOT)).replace("\\", "/"),
        }
    )
    checks.append(
        {
            "name": "worldview_links_formula_json",
            "ok": "mkm12_75_formulas_ssot_v1_latest.json" in wv_text,
        }
    )
    checks.append(
        {
            "name": "worldview_section5_present",
            "ok": "## 5." in wv_text and "수학 헌법" in wv_text,
        }
    )
    checks.append(
        {
            "name": "worldview_section1_3_matching_layer",
            "ok": "### 1.3 Meta-Architecture" in wv_text and "gematria_bridge_v1" in wv_text,
        }
    )
    checks.append(
        {
            "name": "worldview_appendix_media_orchestration",
            "ok": "## 8. 부록: Media Orchestration Lane" in wv_text,
        }
    )
    checks.append(
        {
            "name": "worldview_appendix_parable_prophecy",
            "ok": "## 9. 부록: 비유(Parable) vs 예언(Prophecy)" in wv_text,
        }
    )
    checks.append(
        {
            "name": "worldview_metrics_current",
            "ok": bool(
                re.search(r"documented_with_expr[^\d]*75", wv_text)
                and "unrecovered_slots: 0" in wv_text
            ),
        }
    )

    ascii_ok = ASCII_POINTER.is_file()
    ascii_text = _read(ASCII_POINTER) if ascii_ok else ""
    checks.append(
        {
            "name": "ascii_pointer_links_worldview",
            "ok": ascii_ok and "MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md" in ascii_text,
        }
    )

    formulas_doc: dict = {}
    if FORMULAS.is_file():
        formulas_doc = json.loads(_read(FORMULAS))
    refs = formulas_doc.get("references") or {}
    checks.append(
        {
            "name": "formula_json_links_worldview",
            "ok": "worldview_constitution" in refs
            and "MKM_WORLDVIEW" in str(refs.get("worldview_constitution", "")),
        }
    )
    checks.append(
        {
            "name": "formula_slots_complete",
            "ok": int(formulas_doc.get("unrecovered_slots", 99)) == 0
            and int(formulas_doc.get("documented_with_expr", 0)) == 75,
        }
    )
    checks.append(
        {
            "name": "repo_fact_count",
            "ok": len(formulas_doc.get("repo_implemented_facts", [])) == 4,
        }
    )

    promo_ok = False
    if PROMOTION.is_file():
        promo = json.loads(_read(PROMOTION))
        promo_ok = promo.get("promotion_to_a_track_allowed") is False and len(
            promo.get("entries", [])
        ) == 75
    checks.append(
        {
            "name": "promotion_registry_track_wall",
            "ok": promo_ok,
        }
    )

    canon_ok = CANON.is_file() and "MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md" in _read(
        CANON
    )
    checks.append(
        {
            "name": "theory_canon_links_worldview",
            "ok": canon_ok,
        }
    )

    doc = {
        "schema": "worldview_formula_crosslink_bridge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "track_b_only": True,
        "promotion_to_a_track_allowed": False,
        "worldview_section": "§5",
        "worldview_appendix_sections": ["§1.3", "§8", "§9"],
        "worldview_version": "v1.1",
        "pointers": {
            "worldview": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
            "worldview_matching_layer": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md#13-meta-architecture-matching-layer-a-layer",
            "worldview_media_orchestration": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md#8-부록-media-orchestration-lane-a-layer",
            "worldview_parable_prophecy": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md#9-부록-비유parable-vs-예언prophecy-a-layer",
            "cosmic_meta_arch_draft": "docs/final/artifacts/logos_cosmic_meta_architecture_draft_v1_latest.json",
            "formulas_json": "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json",
            "ascii_pointer": "docs/final/MKM12_75_FORMULAS_SSOT_V1.md",
            "theory_canon": "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
            "promotion_registry": "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json",
        },
        "checks": checks,
        "ok": all(c.get("ok") for c in checks),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "ok": doc["ok"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
