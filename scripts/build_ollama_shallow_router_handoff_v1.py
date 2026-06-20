#!/usr/bin/env python3
"""Build Deep-layer handoff stub from shallow router output v1.

Maps shallow packet -> semantic_rag_bridge lens_route hint only (no RAG fetch).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/ollama_shallow_router_handoff_v1_latest.json"
DOMAIN_TO_LENS = {
    "logos": "logos",
    "myeongni": "myeongni",
    "sasang": "sasang",
    "oracle": "logos",
    "infra": "infra",
    "devops": "infra",
    "design": "design",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_handoff(shallow: dict[str, Any]) -> dict[str, Any]:
    domain = str(shallow.get("domain_tag") or "").strip().lower()
    lens_id = DOMAIN_TO_LENS.get(domain, "infra")
    coords = shallow.get("coordinates") if isinstance(shallow.get("coordinates"), dict) else {}
    anchors = shallow.get("anchor_ids") if isinstance(shallow.get("anchor_ids"), list) else []
    return {
        "schema": "ollama_shallow_router_handoff_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "shallow_source_schema": shallow.get("schema"),
        "lens_route_hint": {
            "lens_id": lens_id,
            "domain_tag": domain,
            "route_confidence_0_1": 0.5,
        },
        "coordinates_slkm": {
            "S": float(coords.get("S", 0.25)),
            "L": float(coords.get("L", 0.25)),
            "K": float(coords.get("K", 0.25)),
            "M": float(coords.get("M", 0.25)),
        },
        "anchor_ids": [str(x) for x in anchors[:3]],
        "deep_fetch_next": [
            "scripts/run_question_semantic_rag_bridge_chain_v1.py",
            "scripts/build_semantic_rag_bridge_insight_bundle_v1.py",
        ],
        "policy": {
            "track": "B-track",
            "gating": "advisory",
            "non_gating_logos": domain == "logos",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Shallow router -> Deep handoff stub v1")
    ap.add_argument("--input-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    shallow = _read_json(args.input_json)
    if shallow.get("schema") != "ollama_shallow_router_output_v1":
        raise SystemExit("input schema must be ollama_shallow_router_output_v1")
    out_doc = build_handoff(shallow)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
