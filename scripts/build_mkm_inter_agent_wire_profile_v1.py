#!/usr/bin/env python3
"""Emit mkm_inter_agent_wire_profile_v1.json from v0 + M6 envelope contract."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V0 = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json"
OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_profile_v1.json"


def build() -> dict:
    base = json.loads(V0.read_text(encoding="utf-8")) if V0.is_file() else {}
    doc = dict(base)
    doc["schema"] = "mkm_inter_agent_wire_profile_v1"
    doc["version"] = "1.0.0"
    doc["status"] = "draft_contract"
    doc["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["wire_envelope"] = {
        "schema": "mkm_inter_agent_wire_envelope_v1",
        "wire_format_version": "1.0.0",
        "json_schema": "docs/final/schemas/mkm_inter_agent_wire_envelope_v1.schema.json",
        "library": "scripts/mkm_inter_agent_wire_envelope_v1.py",
        "runtime_adapter": "scripts/mkm_inter_agent_wire_runtime_adapter_v1.py",
        "http_turn_route": "POST /v1/research/mkm_inter_agent_wire/turn",
        "payload_kind": "lexicon_atom_wire",
        "research_only": True,
    }
    doc["research_optional_flags"] = {
        "use_ko_health_sidecar": {
            "default": False,
            "hypothesis_tier": "B",
            "routes": [
                "POST /v1/research/mkm_lexicon_wire/encode",
                "POST /v1/research/mkm_inter_agent_wire/turn",
            ],
            "fixture": "docs/final/artifacts/mkm_inter_agent_ko_health_sidecar_lexicon_v1.json",
            "note": "[HYPO] KO health overlay; not merged into 41k codebook.",
        }
    }
    ops = dict(doc.get("operations") or {})
    ops["wire_turn_send"] = "POST /v1/research/mkm_inter_agent_wire/turn"
    ops["wire_first_dialogue"] = "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py"
    ops["wire_vs_packet_bench"] = "scripts/run_mkm_inter_agent_wire_vs_packet_bench_v1.py"
    doc["operations"] = ops
    doc["boundary_ack"] = (
        "Wire profile v1 adds turn envelope on top of v0 packet/lexicon layers. "
        "Not production lingua franca SLA."
    )
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
