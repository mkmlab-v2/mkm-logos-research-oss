#!/usr/bin/env python3
"""M25: Gloss session report enriched with batch health sidecar metadata."""

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

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_sidecar_enriched_v1_latest.json"
DEFAULT_BATCH = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_enriched(*, batch_path: Path = DEFAULT_BATCH, turns: int = 4) -> dict[str, Any]:
    from scripts.build_mkm_inter_agent_wire_gloss_session_report_v1 import build_report
    from scripts.export_mkm_inter_agent_wire_sessions_batch_v1 import export_batch

    if not batch_path.is_file():
        batch = export_batch(turns=turns, sidecar_scenarios=("health",))
        batch_path.parent.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))

    report = build_report(batch_manifest_path=batch_path, turns=turns, run_batch_if_missing=False)
    if not report.get("ok"):
        return {"ok": False, "error": "gloss_report_failed"}

    summary = report.get("scenario_summary") or {}
    sessions = batch.get("sessions") or {}
    health = summary.get("health") or {}
    trading = summary.get("trading") or {}

    dial_path = ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json"
    dial_uplift = None
    if dial_path.is_file():
        dial_uplift = json.loads(dial_path.read_text(encoding="utf-8")).get("uplift_avg_atom_id_count")

    sidecar_analysis = {
        "batch_sidecar_scenarios": batch.get("sidecar_scenarios"),
        "health_session_use_sidecar": (sessions.get("health") or {}).get("use_ko_health_sidecar"),
        "health_avg_atom_id_count": health.get("avg_atom_id_count"),
        "trading_avg_atom_id_count": trading.get("avg_atom_id_count"),
        "dialogue_capture_uplift_avg_atoms": dial_uplift,
        "health_empty_turn_count": health.get("empty_turn_count"),
    }

    ok = bool((sessions.get("health") or {}).get("use_ko_health_sidecar")) and float(health.get("avg_atom_id_count") or 0) > 1.0

    return {
        "ok": ok,
        "schema": "mkm_inter_agent_wire_gloss_sidecar_enriched_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "gloss_report": {
            "scenario_summary": summary,
            "batch_manifest": batch_path.relative_to(ROOT).as_posix(),
        },
        "sidecar_analysis": sidecar_analysis,
        "boundary_ack": "Enriched gloss for operator review; not production decode quality claim.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--batch-manifest", type=Path, default=DEFAULT_BATCH)
    ap.add_argument("--turns", type=int, default=4)
    args = ap.parse_args()
    doc = build_enriched(batch_path=args.batch_manifest, turns=max(2, args.turns))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
