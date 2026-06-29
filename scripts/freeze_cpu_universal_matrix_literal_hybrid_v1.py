#!/usr/bin/env python3
"""Freeze CPU Universal Matrix best combo (literal hybrid, 1103) — B-track outpost SSOT."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
BASELINE_DIR = PILOT / "baselines" / "router_tuning_v1"
ARTIFACTS = ROOT / "docs" / "final" / "artifacts"

SOURCES: dict[str, Path] = {
    "sweep_full1103": PILOT / "comp_universal_bench_matrix_sweep_router_hybrid_v1_literal_full1103.json",
    "by_lane_full1103": PILOT
    / "comp_universal_bench_matrix_sweep_by_lane_router_hybrid_v1_literal_full1103_latest.json",
    "ab_by_lane_full1103": PILOT
    / "comp_universal_matrix_router_ab_by_lane_hybrid_v1_literal_full1103_latest.json",
    "hybrid_profiles": ARTIFACTS / "router_hybrid_stress_lane_profiles_v1.json",
}

FROZEN_NAMES: dict[str, str] = {
    "sweep_full1103": "comp_universal_bench_matrix_sweep_cpu_literal_hybrid_full1103_frozen.json",
    "by_lane_full1103": "comp_universal_bench_matrix_sweep_by_lane_cpu_literal_hybrid_full1103_frozen.json",
    "ab_by_lane_full1103": "comp_universal_matrix_router_ab_cpu_literal_hybrid_full1103_frozen.json",
    "hybrid_profiles": "router_hybrid_stress_lane_profiles_v1_1_1_0_frozen.json",
}

CLOSURE_OUT = PILOT / "comp_universal_matrix_cpu_outpost_closure_v1.json"
POINTER_OUT = ARTIFACTS / "CPU_UNIVERSAL_MATRIX_CPU_OUTPOST_FREEZE_POINTER_V1.json"
MANIFEST_OUT = BASELINE_DIR / "cpu_universal_matrix_literal_hybrid_freeze_manifest_v1.json"

TRACK_A_FORBIDDEN = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def main() -> int:
    missing = [k for k, p in SOURCES.items() if not p.is_file()]
    if missing:
        print(json.dumps({"error": "missing_sources", "keys": missing}, ensure_ascii=False))
        return 1

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    frozen_paths: dict[str, str] = {}
    file_hashes: dict[str, str] = {}

    for key, src in SOURCES.items():
        dst = BASELINE_DIR / FROZEN_NAMES[key]
        shutil.copy2(src, dst)
        frozen_paths[key] = _rel(dst)
        file_hashes[dst.name] = _sha256(dst)

    ab = json.loads((BASELINE_DIR / FROZEN_NAMES["ab_by_lane_full1103"]).read_text(encoding="utf-8-sig"))
    en = (ab.get("lanes") or {}).get("en_tech_spec_stress_v1") or {}
    en_cand = en.get("candidate") or {}

    manifest: dict[str, Any] = {
        "schema": "cpu_universal_matrix_literal_hybrid_freeze_manifest_v1",
        "frozen_at_utc": _utc(),
        "research_only": True,
        "label": "MKM CPU Universal Matrix optimal combo (literal hybrid, 1103) — outpost frozen",
        "router_variant": "router_hybrid_v1_literal_full1103",
        "runtime_config": {
            "shards_root": "codebook/shards_btrack_router_sharp_v2",
            "lane_shard_overrides_json": "docs/final/artifacts/router_lane_shard_overrides_v1.json",
            "hybrid_profiles_json": "docs/final/artifacts/router_hybrid_stress_lane_profiles_v1.json",
            "hybrid_profiles_version": "1.1.0",
            "build_shards_script": "scripts/build_router_sharp_v2_shards_v1.py",
        },
        "pre_router_baseline": {
            "sweep": "reports/constitution/btrack_pilot/baselines/router_tuning_v1/comp_universal_bench_matrix_sweep_baseline_frozen.json",
            "note": "AB vs this file measures router tuning uplift only.",
        },
        "frozen_files": frozen_paths,
        "sha256": file_hashes,
        "headline_metrics_1103": {
            "global_jaccard_mean_economy_plus_wire": 0.8185194168700793,
            "en_tech_spec_stress_v1_jaccard_min": float(en_cand.get("jaccard_min") or 0.0),
            "en_tech_spec_stress_v1_jaccard_mean": float(en_cand.get("jaccard_mean") or 0.0),
            "en_tech_delta_vs_pre_router_baseline_jaccard_mean": float(en.get("delta_jaccard_mean") or 0.0),
            "jaccard_floor_gate_0_85_passed": False,
        },
        "governance": {
            "track_a_active_written": False,
            "forbidden_write_path": _rel(TRACK_A_FORBIDDEN),
            "cap_grid_sweep_default": "cancelled",
            "next_rail": "[HYPO] semantic_embedding_gpu_btrack — not Track A merge",
        },
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    closure = {
        "schema": "comp_universal_matrix_cpu_outpost_closure_v1",
        "generated_at_utc": manifest["frozen_at_utc"],
        "research_only": True,
        "status": "cpu_outpost_frozen",
        "freeze_manifest": _rel(MANIFEST_OUT),
        "track_a_frozen": {
            "path": _rel(TRACK_A_FORBIDDEN),
            "global_token_saving_rate": 0.475,
            "avg_reconstruction_fidelity_jaccard": 0.890,
            "apply_gematria_4d_bridge_policy": False,
            "note": "Unchanged — Universal Matrix CPU outpost does not promote to Track A.",
        },
        "cpu_outpost_headline": manifest["headline_metrics_1103"],
        "cancelled_by_default": [
            "en_tech_cap_grid_sweep",
            "routine_router_sharp_v1_v2_ab_without_new_hypothesis",
        ],
        "recommended_next_b_track_only": [
            "NVIDIA Inception portal product spec (external)",
            "en_tech OOV / lexicon coverage report from comp_atom02 chain",
            "semantic embedding routing PoC with separate bench + track_a_active_written false",
        ],
        "forbidden_without_human": [
            "overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "claim 0.85 gate passed from CPU universal matrix",
            "merge literal hybrid into MS paste or Golden 40",
        ],
    }
    CLOSURE_OUT.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    pointer = {
        "schema": "cpu_universal_matrix_cpu_outpost_freeze_pointer_v1",
        "version": "1.0.0",
        "research_only": True,
        "ssot_manifest": _rel(MANIFEST_OUT),
        "ssot_closure": _rel(CLOSURE_OUT),
        "one_liner": "CPU rule engine ceiling for Universal Matrix: hybrid literal en_tech + v2 shards; 1103 frozen; 0.85 gate not met.",
    }
    POINTER_OUT.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Extend router_tuning baseline_manifest
    legacy_manifest_path = BASELINE_DIR / "baseline_manifest.json"
    legacy: dict[str, Any] = {}
    if legacy_manifest_path.is_file():
        legacy = json.loads(legacy_manifest_path.read_text(encoding="utf-8-sig"))
    legacy["cpu_universal_matrix_literal_hybrid_freeze"] = {
        "manifest": _rel(MANIFEST_OUT),
        "frozen_at_utc": manifest["frozen_at_utc"],
        "sha256": file_hashes,
    }
    legacy_manifest_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "wrote_manifest": _rel(MANIFEST_OUT),
                "wrote_closure": _rel(CLOSURE_OUT),
                "wrote_pointer": _rel(POINTER_OUT),
                "en_tech_jaccard_min": manifest["headline_metrics_1103"]["en_tech_spec_stress_v1_jaccard_min"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
