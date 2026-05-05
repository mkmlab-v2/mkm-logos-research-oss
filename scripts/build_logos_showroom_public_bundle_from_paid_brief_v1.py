#!/usr/bin/env python3
"""Build showroom_public_bundle_v1 from Logos paid brief artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _event_id(ts: str) -> str:
    digest = hashlib.sha1(ts.encode("utf-8")).hexdigest()[:8]
    return f"logos-brief-{ts.replace(':', '').replace('-', '')}-{digest}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--brief-json", type=Path, default=ART / "logos_symbolic_paid_user_brief_latest.json")
    ap.add_argument("--stress-json", type=Path, default=ART / "logos_symbolic_paid_brief_stress_test_latest.json")
    ap.add_argument("--out-json", type=Path, default=ART / "logos_showroom_public_bundle_latest.json")
    args = ap.parse_args()

    brief = _load(Path(args.brief_json).resolve())
    stress = _load(Path(args.stress_json).resolve())
    ts = _now()
    one_line = brief.get("one_line_decision") if isinstance(brief.get("one_line_decision"), dict) else {}
    action = str(one_line.get("action") or "WATCH").upper()
    signal = "HOLD" if action in {"HOLD", "WATCH"} else action
    confidence = int(brief.get("confidence_score_0_100") or 0)
    risk_level = "WARNING" if signal in {"HOLD", "WATCH"} else "NORMAL"
    stress_summary = stress.get("summary") if isinstance(stress.get("summary"), dict) else {}
    stress_status = str(stress.get("status") or "unknown")
    scenario_count = int(stress_summary.get("scenario_count") or 0)
    fail_count = int(stress_summary.get("fail_count") or 0)

    bundle = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": ts,
        "runner": "scripts/build_logos_showroom_public_bundle_from_paid_brief_v1.py",
        "sources": {
            "paid_brief": str(Path(args.brief_json).resolve()).replace("\\", "/"),
            "stress_test": str(Path(args.stress_json).resolve()).replace("\\", "/"),
        },
        "observability": {
            "track_b_non_gating": True,
            "logos_paid_brief_present": True,
            "logos_stress_status": stress_status,
            "logos_stress_scenario_count": scenario_count,
            "logos_stress_fail_count": fail_count,
        },
        "public_event_v1": {
            "timestamp": ts,
            "active_character_id": "logos_guardian",
            "risk_level": risk_level,
            "public_signal_direction": signal,
            "abstract_reason": str(one_line.get("message_ko") or "manual gate based public brief."),
            "schema_version": "public-event.v1",
            "event_id": _event_id(ts),
            "source": "ops_showroom_bundle_v1",
            "direction_abstract": signal.lower(),
            "disclaimer_ref": "jemaai_showroom_v1",
            "showroom_display_mode": "defend" if signal == "HOLD" else "idle",
            "showroom_ticker_key": f"L_{signal}_C{confidence}",
            "showroom_reaction_line_ids": ["R_MODE_DEF_01"] if signal == "HOLD" else ["R_MODE_IDLE_01"],
            "delayed_metrics": {
                "delay_seconds": 180,
                "logos_x_index_0_100": confidence,
                "logos_x_band": "HIGH" if confidence >= 80 else ("MID" if confidence >= 50 else "LOW"),
                "logos_quadrant": "Q1" if signal in {"HOLD", "WATCH"} else "Q2",
                "logos_graph_bundle_present": False,
                "logos_graph_staleness_seconds": 0,
                "logos_paid_brief_source": "logos_paid_brief_v1",
            },
        },
    }

    out = Path(args.out_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

