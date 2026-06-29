#!/usr/bin/env python3
"""[HYPO] Assemble jemaai public-event.v1 shadow ingest packet when prophecy gates are auto_promote_ready.

Does NOT enable live trading, Track A merge, or order routing. POST is a separate operator step.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_GATES = ART / "prophecy_promotion_gates_v1_latest.json"
DEFAULT_GO = ART / "trading_go_no_go_latest.json"
DEFAULT_DIR_HIT = REPORTS / "btrack_fills_prophecy_direction_hit_v1_latest.json"
DEFAULT_JOIN_META = REPORTS / "btrack_fills_prophecy_join_wide_v1_latest.meta.json"
DEFAULT_HUMAN = ART / "btrack_align_panel_auto_promote_human_review_v1_latest.json"
DEFAULT_OUT = ART / "btrack_prophecy_jemaai_shadow_ingest_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _map_public_direction(gates: dict[str, Any]) -> str:
    rec = str(gates.get("promotion_recommendation") or "").lower()
    if "hold" in rec or not gates.get("auto_promote_ready"):
        return "HOLD"
    return "WATCH"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gates-json", type=Path, default=DEFAULT_GATES)
    ap.add_argument("--go-no-go-json", type=Path, default=DEFAULT_GO)
    ap.add_argument("--direction-hit-json", type=Path, default=DEFAULT_DIR_HIT)
    ap.add_argument("--join-meta-json", type=Path, default=DEFAULT_JOIN_META)
    ap.add_argument("--human-review-json", type=Path, default=DEFAULT_HUMAN)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--allow-go-trading",
        action="store_true",
        help="Skip NO_GO guard (default refuses when go_no_go != NO_GO).",
    )
    args = ap.parse_args(argv)

    gates = _load(args.gates_json)
    if not gates.get("auto_promote_ready"):
        print(f"refusing packet: auto_promote_ready is not true in {args.gates_json}", file=sys.stderr)
        return 2

    go_doc = _load(args.go_no_go_json)
    go_status = str(go_doc.get("go_no_go") or "").upper()
    if go_status != "NO_GO" and not args.allow_go_trading:
        print(
            f"refusing packet: trading go_no_go={go_status!r} (expected NO_GO); "
            "shadow ingest blocked while live path may be open",
            file=sys.stderr,
        )
        return 3

    human = _load(args.human_review_json) if args.human_review_json.is_file() else {}
    dir_hit = _load(args.direction_hit_json)
    join_meta = _load(args.join_meta_json)

    ts = _utc()
    event_id = f"btrack-prophecy-shadow-{ts[:10].replace('-', '')}"
    public_dir = _map_public_direction(gates)

    ohlcv_hit = None
    ohlcv = dir_hit.get("ohlcv_leg") if isinstance(dir_hit.get("ohlcv_leg"), dict) else {}
    if ohlcv.get("directional_hit_rate") is not None:
        ohlcv_hit = ohlcv.get("directional_hit_rate")

    packet: dict[str, Any] = {
        "schema": "btrack_prophecy_jemaai_shadow_ingest_packet_v1",
        "generated_at_utc": ts,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "ingest_ready": bool(human.get("decision")),
        "human_review_required": True,
        "explicit_hold": {
            "live_trading_auto_enable": False,
            "track_a_auto_merge": False,
            "order_routing": False,
            "ms_headline_kpi_update": False,
        },
        "gate_snapshot": {
            "auto_promote_ready": gates.get("auto_promote_ready"),
            "strict_passed": gates.get("strict_passed"),
            "strict_pass_streak": gates.get("strict_pass_streak"),
            "combined_all_passed": gates.get("combined_all_passed"),
            "outcome_class": gates.get("outcome_class"),
            "go_no_go": go_status or None,
            "risk_mode": go_doc.get("risk_mode"),
        },
        "shadow_measurement": {
            "overlap_days": (join_meta.get("counts") or {}).get("n_overlap_days"),
            "fills_only_days": (join_meta.get("counts") or {}).get("n_fills_only_days"),
            "direction_hit_ohlcv": ohlcv_hit,
            "direction_hit_note_ko": "방향 적중률은 연구 측정치; 승격·실매매 근거 아님.",
        },
        "evidence": {
            "gates": _rel(args.gates_json),
            "go_no_go": _rel(args.go_no_go_json),
            "direction_hit": _rel(args.direction_hit_json) if dir_hit else None,
            "join_meta": _rel(args.join_meta_json) if join_meta else None,
            "human_review": _rel(args.human_review_json) if human else None,
        },
        "public_event_v1": {
            "timestamp": ts,
            "schema_version": "public-event.v1",
            "event_id": event_id,
            "source": "btrack_prophecy_shadow_ingest_v1",
            "active_character_id": "bear_shield",
            "system_status": "shadow_observation",
            "risk_level": "INFO",
            "public_signal_direction": public_dir,
            "direction_abstract": "flat",
            "abstract_reason": (
                "B-track prophecy auto_promote_ready shadow observation — "
                "no orders, balances, or live routing. [HYPO] research_only."
            ),
            "disclaimer_ref": "jemaai_showroom_v1",
            "last_ok_utc": ts,
            "showroom_display_mode": "idle",
            "showroom_ticker_key": "S_SHADOW_R_INFO_PSD_HOLD_DA_FLAT",
            "showroom_reaction_line_ids": ["R_MODE_IDLE_01"],
            "delayed_metrics": {
                "delay_seconds": 300,
                "as_of_utc": ts,
                "prophecy_strict_pass_streak": gates.get("strict_pass_streak"),
            },
        },
        "ingest": {
            "default_url_env": "SHOWROOM_INGEST_URL",
            "token_env": "PUBLIC_EVENT_GATEWAY_TOKEN",
            "post_command": "scripts/Run-BtrackProphecyJemaaiShadowIngest_v1.ps1 -Post",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
