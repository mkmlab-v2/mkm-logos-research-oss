#!/usr/bin/env python3
"""Emit SSOT: whether Track A/B ultra-compression artifacts feed B-track LLM bundle (read-only audit)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "compression_prophecy_bridge_status_v1_latest.json"
BUNDLE_BUILDER = ROOT / "scripts" / "build_btrack_llm_input_bundle.py"
DEFAULT_BUNDLE = ROOT / "docs" / "final" / "artifacts" / "btrack_llm_input_bundle_latest.json"
HYPOTHESIS_GEN = ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"

# Mirrored from build_btrack_llm_input_bundle.py defaults (keep in sync if that script changes).
BUNDLE_DEFAULT_INPUTS: tuple[tuple[str, Path], ...] = (
    ("myeongni_independent_lens", ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"),
    ("sasang_independent_lens", ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"),
    ("logos_independent_lens", ROOT / "docs/final/artifacts/logos_independent_lens_latest.json"),
    ("independent_lens_fusion_stub", ROOT / "docs/final/artifacts/independent_lens_fusion_stub_latest.json"),
    ("independent_lens_shadow_minority_monthly", ROOT / "docs/final/artifacts/independent_lens_shadow_minority_monthly_latest.json"),
    ("news_independent_lens", ROOT / "docs/final/artifacts/news_independent_lens_latest.json"),
    ("macro_independent_lens", ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"),
    ("compression_kpi_summary", ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"),
    ("compression_active_report", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"),
    ("compression_decision", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"),
)

# Known compression / multilens bench outputs that would count as a physical wire if referenced.
COMPRESSION_WIRE_CANDIDATES: tuple[tuple[str, Path], ...] = (
    ("multilens_ultra_active_report", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"),
    ("multilens_ultra_active_literal", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json"),
    ("multilens_ultra_active_ultra_literal", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json"),
    ("ultra_compression_kpi_summary", ROOT / "reports/constitution/btrack_pilot/ultra_compression_kpi_summary_latest.json"),
    ("multilens_ultra_decision", ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"),
)

# If any of these appear in bundle builder source, treat as wired-by-code (string-level audit).
BUILDER_COMPRESSION_TOKENS: tuple[str, ...] = (
    "MULTILENS_ULTRA_COMPRESSION",
    "ultra_compression_kpi",
    "run_ultra_compression",
    "compression_weekly_governance",
    "MULTILENS_PERFORMANCE_EVAL_INPUT_V2",
)

DEFAULT_INTERPRETIVE = ROOT / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"

BUILDER_INTERPRETIVE_TOKENS: tuple[str, ...] = (
    "sasang_interpretive_bridge_context",
    "sasang_interpretive_insight_bundle",
    "interpretive_bridge_payload",
    "btrack_interpretive_bridge_v1",
)

HYPOTHESIS_INTERPRETIVE_TOKENS: tuple[str, ...] = (
    "interpretive_bridge",
    "interpretive_bridge_available",
    "interpretive_bridge_weight_adjustment_applied",
)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _builder_references_compression(builder_src: str) -> bool:
    return any(tok in builder_src for tok in BUILDER_COMPRESSION_TOKENS)


def _bundle_snapshot_wires(bundle_doc: dict[str, Any]) -> list[str]:
    wired: list[str] = []
    paths = bundle_doc.get("artifact_paths")
    if not isinstance(paths, dict):
        return wired
    blob = json.dumps(paths, ensure_ascii=False)
    for cid, cpath in COMPRESSION_WIRE_CANDIDATES:
        rel = cpath.relative_to(ROOT).as_posix()
        if rel in blob or str(cpath.resolve()) in blob:
            wired.append(cid)
    return wired


def _hypothesis_gen_references_compression(src: str) -> bool:
    return any(tok in src for tok in BUILDER_COMPRESSION_TOKENS)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build compression↔B-track prophecy bridge status (Fact-Lock audit artifact)."
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 2 if bridge_status is not wired (for optional CI gates).",
    )
    args = ap.parse_args()

    builder_src = _read_text(BUNDLE_BUILDER)
    hypo_src = _read_text(HYPOTHESIS_GEN)
    builder_hits = [t for t in BUILDER_COMPRESSION_TOKENS if t in builder_src]
    hypo_hits = [t for t in BUILDER_COMPRESSION_TOKENS if t in hypo_src]

    bundle_path = DEFAULT_BUNDLE
    bundle_doc: dict[str, Any] = {}
    snapshot_wired: list[str] = []
    if bundle_path.is_file():
        try:
            bundle_doc = json.loads(bundle_path.read_text(encoding="utf-8"))
            if isinstance(bundle_doc, dict):
                snapshot_wired = _bundle_snapshot_wires(bundle_doc)
        except json.JSONDecodeError:
            bundle_doc = {"_parse_error": True}

    builder_refs = _builder_references_compression(builder_src)
    hypo_refs = _hypothesis_gen_references_compression(hypo_src)

    wired_paths: list[str] = []
    if snapshot_wired:
        wired_paths.extend(snapshot_wired)
    if builder_refs:
        wired_paths.append("builder_source:token_match")
    if hypo_refs:
        wired_paths.append("hypothesis_gen_source:token_match")

    if snapshot_wired or builder_refs or hypo_refs:
        bridge_status = "wired_partial_v1"
    else:
        bridge_status = "not_wired_v1"

    candidates_out = []
    for cid, cpath in COMPRESSION_WIRE_CANDIDATES:
        candidates_out.append(
            {
                "id": cid,
                "path": cpath.relative_to(ROOT).as_posix(),
                "exists": cpath.is_file(),
            }
        )

    interpretive_builder_hits = [t for t in BUILDER_INTERPRETIVE_TOKENS if t in builder_src]
    interpretive_hypo_hits = [t for t in HYPOTHESIS_INTERPRETIVE_TOKENS if t in hypo_src]
    bundle_arts = bundle_doc.get("artifacts") if isinstance(bundle_doc.get("artifacts"), dict) else {}
    interpretive_artifact = (
        bundle_arts.get("sasang_interpretive_bridge_context") if isinstance(bundle_arts, dict) else {}
    )
    if not isinstance(interpretive_artifact, dict):
        interpretive_artifact = {}
    ib_available = bool(interpretive_artifact.get("available"))
    ib_guards = (
        interpretive_artifact.get("auto_weight_adjustment_forbidden") is True
        and interpretive_artifact.get("track_a_live_routing_forbidden") is True
    )
    if ib_available and ib_guards and interpretive_builder_hits:
        interpretive_bridge_status = "wired_read_only_v1"
    elif interpretive_builder_hits or interpretive_hypo_hits:
        interpretive_bridge_status = "wired_partial_v1"
    else:
        interpretive_bridge_status = "not_wired_v1"

    out = {
        "schema": "compression_prophecy_bridge_status_v1",
        "version": "1.1.0",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bridge_status": bridge_status,
        "wired_paths": sorted(set(wired_paths)),
        "bundle_builder_script": BUNDLE_BUILDER.relative_to(ROOT).as_posix(),
        "bundle_default_inputs": [{"slot": k, "path": p.relative_to(ROOT).as_posix()} for k, p in BUNDLE_DEFAULT_INPUTS],
        "bundle_latest_path": bundle_path.relative_to(ROOT).as_posix(),
        "bundle_snapshot_wired_ids": snapshot_wired,
        "builder_source_compression_token_hits": builder_hits,
        "hypothesis_gen_compression_token_hits": hypo_hits,
        "compression_wire_candidates": candidates_out,
        "interpretive_bridge": {
            "bridge_status": interpretive_bridge_status,
            "bundle_slot": "artifacts.sasang_interpretive_bridge_context",
            "source_bundle_path": DEFAULT_INTERPRETIVE.relative_to(ROOT).as_posix(),
            "source_bundle_exists": DEFAULT_INTERPRETIVE.is_file(),
            "snapshot_available": ib_available,
            "snapshot_axis_count": interpretive_artifact.get("axis_count"),
            "safety_flags_ok": ib_guards if ib_available else None,
            "builder_token_hits": interpretive_builder_hits,
            "hypothesis_gen_token_hits": interpretive_hypo_hits,
            "weight_adjustment_applied_in_hypothesis": False,
            "fact_safe_note": "Interpretive bridge is read-only human_only context. "
            "Does not prove pathology→TE mapping or Track A promotion.",
        },
        "fact_safe_note": "String scan + path presence only; does not prove causal impact on hit rate. "
        "A real bridge requires an explicit field in btrack_llm_input_bundle_v1 and builder wiring.",
        "out_of_scope": "No live trading; no automatic promotion; B-track remains hypothesis_tier B.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} bridge_status={bridge_status}")

    if args.strict_exit and bridge_status != "wired_partial_v1":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
