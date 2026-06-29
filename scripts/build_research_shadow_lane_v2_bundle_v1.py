#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge shadow lane v1 + symbolic energy + imagination rail -> showroom v2 JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHADOW = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
DEFAULT_SYMBOLIC = ROOT / "docs/final/artifacts/job_prologue_symbolic_energy_v1_latest.json"
DEFAULT_IMAGINATION = ROOT / "docs/final/artifacts/logos_imagination_rail_envelope_v1_latest.json"
DEFAULT_OUT = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_research_shadow_lane_v2.json"
)
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/research_shadow_lane_v2_bundle_v1_latest.json"

SCHEMA_VERSION = "research_shadow_lane_v2_bundle_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build research shadow lane v2 bundle.")
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--symbolic-json", type=Path, default=DEFAULT_SYMBOLIC)
    ap.add_argument("--imagination-json", type=Path, default=DEFAULT_IMAGINATION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-artifact", type=Path, default=DEFAULT_OUT_ART)
    args = ap.parse_args()

    def _p(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    shadow = _load(_p(args.shadow_json))
    symbolic = _load(_p(args.symbolic_json))
    imagination = _load(_p(args.imagination_json))

    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now(),
        "issue_id": shadow.get("issue_id"),
        "query_ko": shadow.get("query_ko"),
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "note_ko": (
                "Shadow Lane v2: 서사 경계(v1) + 상징·에너지 망 + 상상력 레일. "
                "환각 제거 주장 없음 — imagination_path 격리."
            ),
        },
        "rail_status": shadow.get("rail_status"),
        "layers": {
            "narrative_boundary": shadow,
            "symbolic_energy": symbolic,
            "imagination_rail": imagination,
        },
        "high_dim_hypotheses": symbolic.get("high_dim_hypotheses") or [],
        "reproduce": {
            "chain": "powershell -File scripts/run_research_shadow_lane_v2_chain_v1.ps1",
        },
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    out_json = _p(args.out_json)
    out_art = _p(args.out_artifact)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_art.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(payload, encoding="utf-8")
    out_art.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
