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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    rows = _rows()
    out_doc = {
        "schema": "pointerguard_folder_policy_v1",
        "generated_at_utc": _now_utc(),
        "policy_default": "deny_unless_allowlisted",
        "research_only": True,
        "source_track": "B",
        "rows": rows,
        "summary": {
            "apply_count": sum(1 for r in rows if r["policy"] == "apply"),
            "caution_count": sum(1 for r in rows if r["policy"] == "caution"),
            "forbid_count": sum(1 for r in rows if r["policy"] == "forbid"),
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "summary": out_doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
