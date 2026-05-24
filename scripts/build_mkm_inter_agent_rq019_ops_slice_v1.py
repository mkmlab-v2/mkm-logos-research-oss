#!/usr/bin/env python3
"""M24: Compact operator ops slice for RQ-019 inter-agent wire lane (research_only)."""

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

STATUS = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_ops_slice_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def build_ops_slice(*, status_path: Path = STATUS) -> dict[str, Any]:
    status = _load(status_path)
    if not status:
        return {"ok": False, "error": "encoding_status_missing"}

    health_dial = _load(ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json")
    live_http = _load(ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_live_http_v1_latest.json")
    m3 = _load(ROOT / "docs/final/artifacts/mkm_inter_agent_m3_public_copy_v1_latest.json")
    batch = _load(ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json")

    health_sess = ((batch or {}).get("sessions") or {}).get("health") or {}
    ko_disclaimer = (m3 or {}).get("public_copy", {}).get("ko") if m3 else None

    flags_ok = bool(status.get("rq_019_milestones_core_ready")) and bool(
        status.get("rq_019_milestones_wire_layer_ready")
    )

    doc = {
        "ok": flags_ok and bool(health_dial and health_dial.get("ok")),
        "schema": "mkm_inter_agent_rq019_ops_slice_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "rq_019": status.get("rq_019"),
        "readiness": {
            "core_ready": status.get("rq_019_milestones_core_ready"),
            "wire_layer_ready": status.get("rq_019_milestones_wire_layer_ready"),
            "language_dev_m12_m27_ready": status.get("rq_019_language_dev_m12_m27_ready"),
            "language_dev_m27_ready": status.get("rq_019_language_dev_m27_ready"),
        },
        "health_sidecar_uplift": {
            "dialogue_avg_atom_uplift": (health_dial or {}).get("uplift_avg_atom_id_count"),
            "live_http_avg_atoms": (live_http or {}).get("avg_atom_id_count"),
            "batch_health_sidecar_enabled": health_sess.get("use_ko_health_sidecar"),
        },
        "m3_public_copy_ko_one_line": ko_disclaimer,
        "pointers": status.get("pointers"),
        "boundary_ack": "Ops slice only; not Track A routing, live trading, or external send approval.",
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", type=Path, default=STATUS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_ops_slice(status_path=args.status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
