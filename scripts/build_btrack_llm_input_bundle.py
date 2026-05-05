#!/usr/bin/env python3
"""Assemble B-Track LLM input bundle from independent lens + fusion stub artifacts (read-only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"

DEFAULT_MYEONGNI = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_SASANG = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_LOGOS = ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"
DEFAULT_FUSION = ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"
DEFAULT_MINORITY_MONTHLY = ROOT / "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json"
DEFAULT_NEWS_LENS = ROOT / "docs/final/artifacts/news_independent_lens_latest.json"
DEFAULT_MACRO_LENS = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"
DEFAULT_COMPRESSION_KPI = ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"
DEFAULT_COMPRESSION_ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_COMPRESSION_DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _compression_bridge_payload(
    *,
    compression_kpi: Path,
    compression_active: Path,
    compression_decision: Path,
) -> dict[str, Any]:
    kpi = _read(compression_kpi) or {}
    active = _read(compression_active) or {}
    decision = _read(compression_decision) or {}
    active_kpi = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}
    selected = decision.get("selected_candidate") if isinstance(decision.get("selected_candidate"), dict) else {}
    return {
        "schema": "compression_to_btrack_bridge_slice_v1",
        "bridge_mode": "read_only_observation",
        "track_a_active_kpi": {
            "global_token_saving_rate": active_kpi.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": active_kpi.get("avg_reconstruction_fidelity_jaccard"),
            "ultra_saving_policy_ok": active_kpi.get("ultra_saving_policy_ok"),
            "sensitive_integrity_ok": active_kpi.get("sensitive_integrity_ok"),
        },
        "track_a_selected_candidate": {
            "strategy": selected.get("strategy"),
            "intensity": selected.get("intensity"),
            "global_token_saving_rate": selected.get("global_token_saving_rate"),
            "avg_reconstruction_fidelity_jaccard": selected.get("avg_reconstruction_fidelity_jaccard"),
            "canary_gate_ok": selected.get("canary_gate_ok"),
        },
        "fact_safe_note": "Compression bridge is read-only context for B-track hypothesis explanation. "
        "No live trigger and no automatic A-track promotion.",
        "source_paths": {
            "compression_kpi_summary": str(compression_kpi.resolve()),
            "compression_active_report": str(compression_active.resolve()),
            "compression_decision": str(compression_decision.resolve()),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build btrack_llm_input_bundle_latest.json for LLM hypothesis step.")
    ap.add_argument("--myeongni", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--sasang", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--logos", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--fusion", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--minority-monthly", type=Path, default=DEFAULT_MINORITY_MONTHLY)
    ap.add_argument("--news-lens", type=Path, default=DEFAULT_NEWS_LENS, help="news_independent_lens JSON (adapter output)")
    ap.add_argument("--macro-lens", type=Path, default=DEFAULT_MACRO_LENS, help="macro_independent_lens JSON (adapter output)")
    ap.add_argument("--compression-kpi", type=Path, default=DEFAULT_COMPRESSION_KPI)
    ap.add_argument("--compression-active", type=Path, default=DEFAULT_COMPRESSION_ACTIVE)
    ap.add_argument("--compression-decision", type=Path, default=DEFAULT_COMPRESSION_DECISION)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bundle = {
        "schema": "btrack_llm_input_bundle_v1",
        "version": "1.2.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "label": "[HYPO] LLM input bundle — not A-track; no live trigger.",
        "artifacts": {
            "myeongni_independent_lens": _read(args.myeongni),
            "sasang_independent_lens": _read(args.sasang),
            "logos_independent_lens": _read(args.logos),
            "independent_lens_fusion_stub": _read(args.fusion),
            "independent_lens_shadow_minority_monthly": _read(args.minority_monthly),
            "news_independent_lens": _read(args.news_lens),
            "macro_independent_lens": _read(args.macro_lens),
            "compression_bridge_context": _compression_bridge_payload(
                compression_kpi=args.compression_kpi,
                compression_active=args.compression_active,
                compression_decision=args.compression_decision,
            ),
        },
        "artifact_paths": {
            "myeongni": str(args.myeongni.resolve()),
            "sasang": str(args.sasang.resolve()),
            "logos": str(args.logos.resolve()),
            "fusion": str(args.fusion.resolve()),
            "independent_lens_shadow_minority_monthly": str(args.minority_monthly.resolve()),
            "news_independent_lens": str(args.news_lens.resolve()),
            "macro_independent_lens": str(args.macro_lens.resolve()),
            "compression_kpi_summary": str(args.compression_kpi.resolve()),
            "compression_active_report": str(args.compression_active.resolve()),
            "compression_decision": str(args.compression_decision.resolve()),
        },
        "note": "Feed summarized fields to LLM; do not merge with live trading. Sasang: [NON-MEDICAL] if referenced. "
        "news/macro slots filled when news_independent_lens_latest.json / macro_independent_lens_latest.json exist "
        "(run build_btrack_news_macro_lens_adapters_v1.py). compression_bridge_context is read-only.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
