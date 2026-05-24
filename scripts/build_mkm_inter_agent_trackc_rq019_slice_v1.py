#!/usr/bin/env python3
"""M25: Track C–compatible read-only slice for RQ-019 inter-agent wire lane."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def build_slice() -> dict[str, Any]:
    status = _load("docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json")
    ops = _load("docs/final/artifacts/mkm_inter_agent_rq019_ops_slice_v1_latest.json")
    dial = _load("docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json")

    if not status or not ops:
        return {"ok": False, "error": "status_or_ops_slice_missing"}

    readiness = ops.get("readiness") or {}
    uplift = ops.get("health_sidecar_uplift") or {}

    doc = {
        "ok": bool(ops.get("ok")) and bool(status.get("rq_019_milestones_core_ready")),
        "schema": "mkm_inter_agent_trackc_rq019_slice_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "rq_019": status.get("rq_019"),
        "language_dev_m12_m25_ready": status.get("rq_019_language_dev_m12_m25_ready"),
        "language_dev_m12_m24_ready": status.get("rq_019_language_dev_m12_m24_ready"),
        "core_ready": status.get("rq_019_milestones_core_ready"),
        "wire_layer_ready": status.get("rq_019_milestones_wire_layer_ready"),
        "health_sidecar_uplift_avg_atoms": uplift.get("dialogue_avg_atom_uplift")
        or (dial or {}).get("uplift_avg_atom_id_count"),
        "m3_disclaimer_ko": ops.get("m3_public_copy_ko_one_line"),
        "operator_hint": (
            "Inter-agent wire lane is B-track research_only. "
            "Health KO lines use optional [HYPO] sidecar; not Track A routing."
        ),
        "pointers": ops.get("pointers"),
        "boundary_ack": "Dashboard slice only; no prophecy merge or live trading trigger.",
    }
    return doc


def dashboard_fields(slice_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compact Track C ops dashboard block (read-only; no routing)."""
    doc = slice_doc if slice_doc is not None else build_slice()
    ok = bool(doc.get("ok"))
    return {
        "role": "inter_agent_rq019_research_slice_v1",
        "state": "OK" if ok else "DEGRADED",
        "research_only": True,
        "hypothesis_tier": "B",
        "rq_019": doc.get("rq_019"),
        "language_dev_m12_m25_ready": doc.get("language_dev_m12_m25_ready"),
        "core_ready": doc.get("core_ready"),
        "wire_layer_ready": doc.get("wire_layer_ready"),
        "health_sidecar_uplift_avg_atoms": doc.get("health_sidecar_uplift_avg_atoms"),
        "operator_hint": doc.get("operator_hint"),
        "slice_artifact": "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json",
        "boundary_ack": doc.get("boundary_ack"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_slice()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
