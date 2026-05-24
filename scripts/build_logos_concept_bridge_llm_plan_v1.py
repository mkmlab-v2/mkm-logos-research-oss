#!/usr/bin/env python3
"""Phase2b LLM concept_bridge plan artifact (dry-run, no API call) [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_llm_plan_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = {
        "schema": "logos_concept_bridge_llm_plan_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "execution_mode": "dry_run_no_api",
        "prompt_template_ko": (
            "현대 개념 {concept_ko}를 function→lemma_proxy→verse_ref 3~4단 경로로 분해. "
            "각 path에 note_ko 1문장. prophecy/적중률 주장 금지."
        ),
        "governance": {
            "human_review_required": True,
            "forbidden_fields": ["prophecy_hit_rate", "topology_overlap_percent"],
            "track_wall": "B_track_not_track_A",
        },
        "next_steps": [
            "Gemini batch or MCP with explicit --thinking-budget cap",
            "jsonschema validate logos_concept_bridge_v1",
            "append to logos_concept_bridge_registry_v1",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
