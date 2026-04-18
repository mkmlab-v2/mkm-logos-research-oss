# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.75, L:0.88, K:0.62, M:0.55}
# Balance: 86
# Purpose: Scan canonical B-track insight / NotebookLM / lens / gate paths and emit a reproducible inventory JSON.
# Keywords: btrack, inventory, prism, notebooklm, lens, gates
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_insight_bridge_inventory_v1_latest.json"
PRISM = ROOT / "docs" / "final" / "MKM12_PRISM_INDEX_REGISTRY_V1.json"

SCHEMA = "btrack_insight_bridge_inventory_v1"

# Canonical anchors for Phase 0 map (repo-relative); not exhaustive of all B-track data.
WATCHLIST: list[tuple[str, str]] = [
    ("prism_registry", "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"),
    ("grand_index_map", "docs/final/MKM12_GRAND_INDEX_MAP.md"),
    ("constitution_facts", "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"),
    ("notebooklm_manifest", "docs/NotebookLM_sources_manifest.md"),
    ("notebooklm_core_bridge_pointer", "docs/final/NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER_V1.md"),
    ("notebooklm_mega_jsonl", "reports/notebooklm/btrack_mega_insights_10gb.jsonl"),
    ("notebooklm_mega_latest_jsonl", "reports/notebooklm/btrack_mega_insights_latest.jsonl"),
    ("notebooklm_triage", "reports/notebooklm/btrack_insight_triage_latest.json"),
    ("notebooklm_recommendation_pack", "reports/notebooklm/btrack_insight_recommendation_pack_latest.json"),
    ("notebooklm_kpi", "docs/final/artifacts/btrack_notebooklm_jsonl_kpi_latest.json"),
    ("myeongni_insight_log", "data/myeongni/insight_observation_log.jsonl"),
    ("myeongni_16_state_jsonl", "data/myeongni/myeongni_16_state_experiment_v1.jsonl"),
    ("lens_logos", "docs/final/artifacts/logos_independent_lens_latest.json"),
    ("lens_myeongni", "docs/final/artifacts/myeongni_independent_lens_latest.json"),
    ("lens_sasang", "docs/final/artifacts/sasang_independent_lens_latest.json"),
    ("prophecy_gate_latest", "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"),
    ("prophecy_gate_legacy_strict", "docs/final/artifacts/prophecy_promotion_gates_v1_legacy_strict_latest.json"),
    ("prophecy_gate_panel_calibrated", "docs/final/artifacts/prophecy_promotion_gates_v1_panel_calibrated_latest.json"),
    ("prophecy_streak_legacy", "docs/final/artifacts/prophecy_promotion_strict_streak_legacy_v1.json"),
    ("prophecy_streak_panel", "docs/final/artifacts/prophecy_promotion_strict_streak_panel_calibrated_v1.json"),
    ("signoff_packet", "docs/final/artifacts/btrack_promotion_signoff_packet_v1_latest.json"),
    ("live_ab_summary", "docs/final/artifacts/prophecy_live_ab_summary_v1_latest.json"),
    ("vault_sync_script", "scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1"),
    ("mega_batch_script", "scripts/run_notebooklm_mega_insight_batch.py"),
    ("dual_gate_refresh", "scripts/refresh_prophecy_promotion_gates_dual_v1.py"),
    ("notebooklm_pull_manifest", "docs/final/artifacts/derived/notebooklm_pull_manifest_v1.json"),
    ("agent_memory_ssot", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"),
    ("prophecy_score_insight_sidecar", "docs/final/artifacts/btrack_prophecy_score_insight_sidecar_v1_latest.json"),
    ("prophecy_score_insight_sidecar_schema", "docs/final/schemas/btrack_prophecy_score_insight_sidecar_v1.schema.json"),
    ("prophecy_score_insight_sidecar_script", "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"),
    ("insight_sidecar_lens_hit_agreement", "docs/final/artifacts/btrack_insight_sidecar_lens_hit_agreement_v1_latest.json"),
    ("insight_sidecar_lens_hit_agreement_script", "scripts/eval_btrack_insight_sidecar_lens_hit_agreement_v1.py"),
    ("insight_sidecar_chain_script", "scripts/Run-BtrackInsightSidecarChain.ps1"),
    ("sasang_dynamics_sample_jsonl", "data/sasang/sasang_dynamics_regime_mapping_v1.sample.jsonl"),
    ("sasang_dynamics_calendar_stub_jsonl", "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"),
    ("myeongni_16_state_experiment_jsonl", "data/myeongni/myeongni_16_state_experiment_v1.jsonl"),
    ("myeongni_16_state_calendar_stub_jsonl", "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"),
    ("seed_lens_calendar_stub_script", "scripts/seed_btrack_lens_calendar_stub_jsonl_v1.py"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stat_entry(rel: str) -> dict[str, Any]:
    p = ROOT / rel
    out: dict[str, Any] = {
        "path": rel.replace("\\", "/"),
        "exists": p.exists(),
    }
    if not p.exists():
        return out
    try:
        st = p.stat()
        out["bytes"] = int(st.st_size)
        out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        out["kind"] = "dir" if p.is_dir() else "file"
    except OSError as e:
        out["stat_error"] = str(e)
    return out


def _prism_summary() -> dict[str, Any]:
    if not PRISM.is_file():
        return {"registry_path": str(PRISM.relative_to(ROOT)).replace("\\", "/"), "exists": False}
    try:
        data = json.loads(PRISM.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {"registry_path": "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json", "exists": True, "parse_error": str(e)}
    entries = data.get("entries")
    n = len(entries) if isinstance(entries, list) else 0
    return {
        "registry_path": "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json",
        "exists": True,
        "schema": data.get("schema"),
        "entry_count": n,
    }


def _long_term_memory_hints() -> dict[str, Any]:
    """Local paths only; may be absent (gitignored or not cloned)."""
    candidates = [
        ROOT / ".mkm-memory",
        ROOT / ".cursor" / "mkm-memory",
    ]
    rows: list[dict[str, Any]] = []
    for p in candidates:
        rel = str(p.relative_to(ROOT)).replace("\\", "/") if p.is_relative_to(ROOT) else str(p)
        rows.append({"path": rel, **_stat_entry(rel)})
    return {"candidates": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    paths: list[dict[str, Any]] = []
    for role, rel in WATCHLIST:
        row = {"role": role, **_stat_entry(rel)}
        paths.append(row)

    manifest_stat = _stat_entry("docs/NotebookLM_sources_manifest.md")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "workspace_root_hint": str(ROOT).replace("\\", "/"),
        "prism": _prism_summary(),
        "notebooklm_manifest": manifest_stat,
        "long_term_memory": _long_term_memory_hints(),
        "paths": paths,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
