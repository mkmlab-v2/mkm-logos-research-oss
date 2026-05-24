#!/usr/bin/env python3
"""Aggregate v2 wire shadow JSONL into btrack_pilot summary (research_only)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = ROOT / "reports/constitution/btrack_pilot/v2_wire_shadow_metering_v1.jsonl"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_v2_wire_shadow_metering_summary_v1.json"
ENV_KEY = "V2_WIRE_SHADOW_METERING_LOG_PATH"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_path(arg: Path | None) -> Path:
    if arg is not None:
        return arg
    raw = os.environ.get(ENV_KEY, "").strip()
    return Path(raw) if raw else DEFAULT_LOG


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    log_path = _log_path(args.log_jsonl)
    if not log_path.is_file():
        print(json.dumps({"ok": False, "error": "missing_log", "path": str(log_path)}))
        return 1

    by_case: dict[str, dict[bool, dict[str, Any]]] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        ev = json.loads(line)
        cid = str(ev.get("case_id") or "")
        wire = bool(ev.get("graph_wire_selective_bridge"))
        if cid:
            by_case.setdefault(cid, {})[wire] = ev

    pairs: list[dict[str, Any]] = []
    boost_count = 0
    for cid, arms in sorted(by_case.items()):
        off = arms.get(False) or {}
        on = arms.get(True) or {}
        sav_off = off.get("global_token_saving_rate")
        sav_on = on.get("global_token_saving_rate")
        jac_off = off.get("reconstruction_fidelity_jaccard")
        jac_on = on.get("reconstruction_fidelity_jaccard")
        delta_sav_pp = None
        delta_jac_pp = None
        if sav_off is not None and sav_on is not None:
            delta_sav_pp = (float(sav_on) - float(sav_off)) * 100.0
        if jac_off is not None and jac_on is not None:
            delta_jac_pp = (float(jac_on) - float(jac_off)) * 100.0
        boosted = bool(on.get("graph_wire_bridge_boost"))
        if boosted:
            boost_count += 1
        pairs.append(
            {
                "case_id": cid,
                "saving_off": sav_off,
                "saving_on": sav_on,
                "jaccard_off": jac_off,
                "jaccard_on": jac_on,
                "delta_saving_pp": delta_sav_pp,
                "delta_jaccard_pp": delta_jac_pp,
                "graph_wire_bridge_boost_on_arm": boosted,
            }
        )

    doc = {
        "schema": "comp_v2_wire_shadow_metering_summary_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": {"a_track_auto_promotion": False, "active_report_write": False},
        "source_log": (
            str(log_path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            if log_path.resolve().is_relative_to(ROOT.resolve())
            else str(log_path.resolve()).replace("\\", "/")
        ),
        "case_pairs": len(pairs),
        "bridge_boost_on_wire_arm_count": boost_count,
        "pairs": pairs,
        "headline": (
            f"Shadow v2 wire bench: {len(pairs)} case pairs; "
            f"{boost_count} with bridge_boost on wire arm ([HYPO] staging only)."
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        out_rel = str(args.out_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        out_rel = str(args.out_json.resolve()).replace("\\", "/")
    print(json.dumps({"ok": True, "wrote": out_rel}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
