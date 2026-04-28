#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "pointerguard_folder_policy_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _rows() -> list[dict[str, Any]]:
    return [
        {
            "path_pattern": "docs/final/artifacts/**",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Repeated structured artifacts with high pointer compression potential.",
        },
        {
            "path_pattern": "docs/final/artifacts/**/*.json",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "High-frequency structured artifact payloads.",
        },
        {
            "path_pattern": "docs/final/artifacts/**/*.jsonl",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Append-only structured logs suitable for pointer path.",
        },
        {
            "path_pattern": "reports/**",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "High-volume repetitive operational reports/log summaries.",
        },
        {
            "path_pattern": "reports/**/*.json",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Structured operational snapshots with repeated schema.",
        },
        {
            "path_pattern": "reports/**/*.jsonl",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Event logs with recurring patterns and high volume.",
        },
        {
            "path_pattern": "projects/bitcoin-trading/memory/v2/**",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Operational telemetry payloads with recurring schemas.",
        },
        {
            "path_pattern": "projects/bitcoin-trading/memory/v2/**/*.json",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Structured ops memory snapshots with recurring fields.",
        },
        {
            "path_pattern": "projects/bitcoin-trading/memory/v2/**/*.jsonl",
            "policy": "apply",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": "pointer_primary",
            "reason": "Time-series records with high redundancy.",
        },
        {
            "path_pattern": "reports/**/*.md",
            "policy": "caution",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Narrative reports need conservative handling despite repetition.",
        },
        {
            "path_pattern": "memory/obsidian_vault/llm_wiki/wiki/**",
            "policy": "caution",
            "default_route_mode": "pointer_shadow",
            "go_route_mode": None,
            "reason": "Context-sensitive synthesis content; keep shadow-only unless approved.",
        },
        {
            "path_pattern": "docs/final/**",
            "policy": "caution",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Narrative/SSOT docs require conservative handling.",
        },
        {
            "path_pattern": "data/logos/**/bench/**",
            "policy": "caution",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Benchmark inputs/labels are reproducibility-sensitive.",
        },
        {
            "path_pattern": "scripts/**",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Executable code path; token-level drift risk is unacceptable.",
        },
        {
            "path_pattern": "api-services/**",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "API/runtime behavior must preserve exact semantics.",
        },
        {
            "path_pattern": ".github/workflows/**",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "CI contract files are sensitive to tiny syntax diffs.",
        },
        {
            "path_pattern": ".cursor/**",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Rule/governance files are immutable control-plane assets.",
        },
        {
            "path_pattern": "AGENTS.md",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Agent operation SSOT must remain lossless.",
        },
        {
            "path_pattern": "CLAUDE.md",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Master policy context must remain lossless.",
        },
        {
            "path_pattern": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Constitution SSOT is protected from pointer path.",
        },
        {
            "path_pattern": "data/**",
            "policy": "forbid",
            "default_route_mode": "track_a_primary",
            "go_route_mode": None,
            "reason": "Raw datasets/corpora require byte-level identity.",
        },
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _merge_previous_profile_state(out_path: Path, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not out_path.exists():
        return profiles
    try:
        prev = _read_json(out_path)
    except Exception:
        return profiles
    prev_profiles = prev.get("promotion_profiles", [])
    if not isinstance(prev_profiles, list):
        return profiles
    by_id: dict[str, dict[str, Any]] = {}
    for p in prev_profiles:
        if isinstance(p, dict) and p.get("profile_id"):
            by_id[str(p["profile_id"])] = p
    merged: list[dict[str, Any]] = []
    for p in profiles:
        cur = dict(p)
        pid = str(cur.get("profile_id", ""))
        old = by_id.get(pid)
        if old and "ramp_current_index" in old:
            cur["ramp_current_index"] = int(old.get("ramp_current_index", cur.get("ramp_current_index", 0)))
        merged.append(cur)
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    rows = _rows()
    promotion_profiles = [
        {
            "profile_id": "artifacts_apply",
            "match_patterns": ["docs/final/artifacts/**"],
            "go_promotion_enabled": True,
            "rollout_order": 2,
            "consecutive_samples": 3,
            "apply_row_ratio_min": 0.35,
            "apply_unresolved_max": 4.0,
        },
        {
            "profile_id": "reports_apply",
            "match_patterns": ["reports/**"],
            "go_promotion_enabled": True,
            "rollout_order": 1,
            "consecutive_samples": 3,
            "apply_row_ratio_min": 0.30,
            "apply_unresolved_max": 4.0,
        },
        {
            "profile_id": "memory_v2_apply",
            "match_patterns": ["projects/bitcoin-trading/memory/v2/**"],
            "go_promotion_enabled": False,
            "rollout_order": 3,
            "consecutive_samples": 5,
            "apply_row_ratio_min": 0.40,
            "apply_unresolved_max": 1.0,
            "ramp_unresolved_thresholds": [4.0, 3.0, 2.0, 1.0],
            "ramp_current_index": 0,
            "ramp_required_consecutive_passes": 3,
        },
    ]
    promotion_profiles = _merge_previous_profile_state(out_path, promotion_profiles)
    out_doc = {
        "schema": "pointerguard_folder_policy_v1",
        "generated_at_utc": _now_utc(),
        "policy_default": "deny_unless_allowlisted",
        "research_only": True,
        "source_track": "B",
        "rows": rows,
        "promotion_profiles": promotion_profiles,
        "summary": {
            "apply_count": sum(1 for r in rows if r["policy"] == "apply"),
            "caution_count": sum(1 for r in rows if r["policy"] == "caution"),
            "forbid_count": sum(1 for r in rows if r["policy"] == "forbid"),
            "promotion_profile_count": len(promotion_profiles),
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "summary": out_doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
