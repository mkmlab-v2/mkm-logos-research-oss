#!/usr/bin/env python3
"""Assemble B-Track LLM input bundle from independent lens + fusion stub artifacts (read-only)."""
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

from scripts.core.btrack_interpretive_bridge_v1 import interpretive_bridge_payload
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
DEFAULT_INTERPRETIVE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
DEFAULT_MARKET_MYEONGNI = ROOT / "docs/final/artifacts/market_myeongni_lens_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "docs/final/artifacts/market_sasang_lens_latest.json"


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


def _market_lens_observation_slot(
    path: Path,
    *,
    expected_schema: str,
    lens_id: str,
) -> dict[str, Any]:
    """Thin read-only slice for market overlay lenses (no score recompute)."""
    base: dict[str, Any] = {
        "schema": "btrack_market_lens_observation_slot_v1",
        "bridge_mode": "read_only_observation",
        "lens_id": lens_id,
        "available": False,
        "a_track_autotrigger_forbidden": True,
        "track_a_live_routing_forbidden": True,
        "fact_safe_note": (
            "Market overlay lens context for B-track hypothesis explanation only. "
            "Does not replace myeongni_independent_lens or sasang_independent_lens; no live trigger."
        ),
        "source_path": str(path.resolve()),
    }
    doc = _read(path)
    if not doc or doc.get("schema") != expected_schema:
        return base
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    direction_score: float | None = None
    confidence: float | None = None
    direction_sign = doc.get("direction_sign")
    if expected_schema == "market_sasang_lens_v1":
        fb = doc.get("fusion_bridge") if isinstance(doc.get("fusion_bridge"), dict) else {}
        direction_score = float(fb.get("score_hint") or 0.0)
        direction_score = max(-1.0, min(1.0, direction_score))
        unc = doc.get("uncertainty") if isinstance(doc.get("uncertainty"), dict) else {}
        comp = float(unc.get("composite_uncertainty") or 0.5)
        comp = max(0.0, min(1.0, comp))
        confidence = max(0.0, min(1.0, 1.0 - comp))
        veto = doc.get("veto") if isinstance(doc.get("veto"), dict) else {}
        if veto.get("force_hold"):
            confidence *= 0.25
        if not direction_sign:
            if direction_score > 0:
                direction_sign = "bull"
            elif direction_score < 0:
                direction_sign = "bear"
            else:
                direction_sign = "neutral"
    else:
        direction_score = scores.get("direction_score")  # type: ignore[assignment]
        confidence = scores.get("confidence")  # type: ignore[assignment]
    slot: dict[str, Any] = {
        **base,
        "available": True,
        "artifact_ts_utc": doc.get("ts_utc"),
        "hypothesis_tier": doc.get("hypothesis_tier"),
        "boundary_ack": doc.get("boundary_ack"),
        "direction_score": direction_score,
        "confidence": confidence,
        "direction_sign": direction_sign,
    }
    if expected_schema == "market_sasang_lens_v1":
        unc = doc.get("uncertainty") if isinstance(doc.get("uncertainty"), dict) else {}
        veto = doc.get("veto") if isinstance(doc.get("veto"), dict) else {}
        slot["market_sasang_summary"] = {
            "composite_uncertainty": unc.get("composite_uncertainty"),
            "veto_force_hold": veto.get("force_hold"),
            "veto_reason_codes": list(veto.get("reason_codes") or []),
            "state_vector_sasang_softmax": doc.get("state_vector_sasang_softmax"),
            "direction_hint": (doc.get("fusion_bridge") or {}).get("direction_hint")
            if isinstance(doc.get("fusion_bridge"), dict)
            else None,
        }
    elif expected_schema == "market_myeongni_lens_v1":
        overlay = doc.get("overlay") if isinstance(doc.get("overlay"), dict) else {}
        applied = overlay.get("applied") if isinstance(overlay.get("applied"), dict) else {}
        slot["market_myeongni_summary"] = {
            "upstream_lens_id": overlay.get("upstream_lens_id"),
            "base_direction_score": overlay.get("base_direction_score"),
            "base_confidence": overlay.get("base_confidence"),
            "applied": applied,
        }
    return slot


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
    ap.add_argument("--interpretive", type=Path, default=DEFAULT_INTERPRETIVE)
    ap.add_argument(
        "--skip-interpretive",
        action="store_true",
        help="Omit sasang_interpretive_bridge_context even if interpretive bundle exists.",
    )
    ap.add_argument("--market-myeongni-lens", type=Path, default=DEFAULT_MARKET_MYEONGNI)
    ap.add_argument("--market-sasang-lens", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument(
        "--skip-market-myeongni",
        action="store_true",
        help="Omit market_myeongni_observation_slot even if artifact exists.",
    )
    ap.add_argument(
        "--skip-market-sasang",
        action="store_true",
        help="Omit market_sasang_observation_slot even if artifact exists.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    interpretive_full = None if args.skip_interpretive else _read(args.interpretive)
    interpretive_bridge = interpretive_bridge_payload(
        interpretive_full,
        source_path=args.interpretive,
    )

    market_myeongni_slot = (
        _market_lens_observation_slot(
            args.market_myeongni_lens,
            expected_schema="market_myeongni_lens_v1",
            lens_id="market_myeongni",
        )
        if not args.skip_market_myeongni
        else {
            "schema": "btrack_market_lens_observation_slot_v1",
            "bridge_mode": "read_only_observation",
            "lens_id": "market_myeongni",
            "available": False,
            "skipped": True,
        }
    )
    market_sasang_slot = (
        _market_lens_observation_slot(
            args.market_sasang_lens,
            expected_schema="market_sasang_lens_v1",
            lens_id="market_sasang",
        )
        if not args.skip_market_sasang
        else {
            "schema": "btrack_market_lens_observation_slot_v1",
            "bridge_mode": "read_only_observation",
            "lens_id": "market_sasang",
            "available": False,
            "skipped": True,
        }
    )

    bundle = {
        "schema": "btrack_llm_input_bundle_v1",
        "version": "1.4.0",
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
            "sasang_interpretive_bridge_context": interpretive_bridge,
            "market_myeongni_observation_slot": market_myeongni_slot,
            "market_sasang_observation_slot": market_sasang_slot,
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
            "sasang_interpretive_insight_bundle": str(args.interpretive.resolve()),
            "market_myeongni_lens": str(args.market_myeongni_lens.resolve()),
            "market_sasang_lens": str(args.market_sasang_lens.resolve()),
        },
        "note": "Feed summarized fields to LLM; do not merge with live trading. Sasang: [NON-MEDICAL] if referenced. "
        "news/macro slots filled when news_independent_lens_latest.json / macro_independent_lens_latest.json exist "
        "(run build_btrack_news_macro_lens_adapters_v1.py). market_*_observation_slot are read-only overlays "
        "(run_market_myeongni_lens_v1.py / run_market_sasang_lens_v1.py); no A-track trigger. "
        "compression_bridge_context and sasang_interpretive_bridge_context are read-only; "
        "interpretive slice excludes interpretive_depth_ko.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
