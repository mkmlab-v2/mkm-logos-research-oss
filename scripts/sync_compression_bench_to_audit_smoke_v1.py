#!/usr/bin/env python3
"""Attach Logos audit-smoke appendix to compression open-bench reproduce pack [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FINISH = ROOT / "docs/final/artifacts/logos_commercial_finish_closure_v1_latest.json"
DEPTH = ROOT / "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json"
HEATMAP = ROOT / "reports/logos_canon_book_coverage_heatmap_v1_latest.json"
INTEGRATION = ROOT / "reports/logos_track_b_integration_closure_v1_latest.json"
CLOSURE_100 = ROOT / "docs/final/artifacts/logos_100pct_closure_v1_latest.json"
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
ART = ROOT / "docs/final/artifacts"
REPRODUCE_PACK = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
CONTRIBUTOR_KIT = ROOT / "docs/final/artifacts/compression_open_bench_contributor_kit_v1_latest.json"
DUAL_REPORT = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
SMOKE_OUT = ROOT / "docs/final/artifacts/compression_open_bench_logos_audit_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def _orphan_summary(theme_ids: list[str]) -> dict[str, Any]:
    total_orphan = 0
    themes_with_orphan = 0
    for tid in theme_ids:
        locked = _load(ART / f"logos_deep_research_distill_{tid}_citation_lock_latest.json")
        narr = locked.get("distill_narrative_stub_ko") or {}
        val = narr.get("citation_validation") or narr.get("validation") or {}
        orphans = val.get("orphan_citations") or []
        if orphans:
            themes_with_orphan += 1
            total_orphan += len(orphans)
    return {
        "themes_checked": len(theme_ids),
        "themes_with_orphan_citations": themes_with_orphan,
        "orphan_citation_count": total_orphan,
        "note": "stub distill mode — orphan count expected 0 when llm_invoked=false",
    }


def build_smoke() -> dict[str, Any]:
    finish = _load(FINISH)
    depth = _load(DEPTH)
    heatmap = _load(HEATMAP)
    integration = _load(INTEGRATION)
    closure_100 = _load(CLOSURE_100)
    presets = _load(PRESETS)
    theme_ids = list((presets.get("themes") or {}).keys())

    depth_checks = depth.get("checks") or {}
    citation_valid = (depth_checks.get("citation_valid_themes") or {}).get("value")
    key_verse_rows = (depth_checks.get("key_verse_v2_density") or {}).get("value")
    book_count = (depth_checks.get("book_heatmap_present") or {}).get("value")

    metrics = (integration or {}).get("metrics") or {}
    rag = (closure_100.get("checks") or {}).get("semantic_rag_quality") or {}

    return {
        "schema": "compression_open_bench_logos_audit_smoke_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "forbidden": [
            "merge_with_ms_headline_kpi",
            "theology_to_sales",
            "track_a_auto_promotion",
            "claim_bible_app_superiority",
        ],
        "metrics": {
            "finish_ok": finish.get("finish_ok"),
            "finish_tier": finish.get("finish_tier"),
            "commercial_depth_closure_ok": depth.get("closure_ok"),
            "citation_valid_themes": citation_valid,
            "theme_preset_count": len(theme_ids),
            "graphrag_seed_organic": metrics.get("graphrag_seed_organic"),
            "thematic_hit_at_1": rag.get("thematic_hit_at_1"),
            "key_verse_v2_rows": key_verse_rows,
            "canon_book_count": book_count,
            "macula_edges_built": (_load(ROOT / "reports/logos_macula_themed_ingest_v1_latest.json") or {}).get(
                "edges_built"
            ),
        },
        "orphan_citation_audit": _orphan_summary(theme_ids),
        "reproduce_commands": [
            "py scripts/build_logos_commercial_finish_closure_gate_v1.py",
            "py scripts/run_logos_track_b_commercial_finish_v1.py --skip-macula --skip-dss --skip-phase-m",
        ],
        "exit_code_contract": {
            "0": "gate passed",
            "1": "gate failed or missing artifacts",
            "2": "governance denial (athena_run_v1 only)",
        },
        "track_wall": {
            "track_a_bridge": False,
            "ms_headline_merge_forbidden": True,
            "theology_to_sales_forbidden": True,
        },
        "heatmap_summary": heatmap.get("summary"),
        "reproduce": "py scripts/sync_compression_bench_to_audit_smoke_v1.py --attach-smoke",
    }


def _attach(path: Path, smoke: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    doc = _load(path)
    doc["logos_audit_smoke_appendix"] = {
        "attached_at_utc": _utc(),
        "artifact": str(SMOKE_OUT.relative_to(ROOT)).replace("\\", "/"),
        "metrics_snapshot": smoke.get("metrics"),
        "forbidden_headline_merge": True,
        "reproduce": smoke.get("reproduce"),
    }
    doc["generated_at_utc"] = _utc()
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attach-smoke", action="store_true", help="Merge smoke into reproduce pack + contributor kit")
    ap.add_argument("--out", type=Path, default=SMOKE_OUT)
    args = ap.parse_args()

    smoke = build_smoke()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    attached = 0
    if args.attach_smoke:
        if _attach(REPRODUCE_PACK, smoke):
            attached += 1
        if _attach(CONTRIBUTOR_KIT, smoke):
            attached += 1
        dual = _load(DUAL_REPORT)
        if dual:
            dual["logos_audit_smoke_appendix"] = {
                "artifact": str(args.out.relative_to(ROOT)).replace("\\", "/"),
                "citation_valid_themes": (smoke.get("metrics") or {}).get("citation_valid_themes"),
                "forbidden_headline_merge": True,
            }
            dual["generated_at_utc"] = _utc()
            DUAL_REPORT.write_text(json.dumps(dual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            attached += 1

    ok = bool(smoke.get("metrics", {}).get("finish_ok")) and int(smoke.get("metrics", {}).get("citation_valid_themes") or 0) >= 10
    print(
        json.dumps(
            {
                "ok": ok,
                "out": str(args.out.relative_to(ROOT)),
                "attached_targets": attached,
                "citation_valid_themes": smoke["metrics"].get("citation_valid_themes"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
