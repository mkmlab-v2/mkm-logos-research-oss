# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.85, L:0.88, K:0.55, M:0.72}
# Balance: 86
# Purpose: Two-track prophecy snapshot — trading-theory adjacency vs historical-omen B-rail.
# Keywords: prophecy, two-track, trading, general_prophecy, boundary
from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ART = Path("docs/final/artifacts")
TEMPLATE_DEFAULT = ART / "prophecy_two_track_snapshot_v1_template.json"
PROPHECY_V2_DEFAULT = ART / "kospi_biblical_prophecy_output_v2_latest.json"
GATE_DEFAULT = ART / "kospi_biblical_single_lane_commercial_gate_autonomous_latest.json"
GENERAL_DEFAULT = ART / "general_prophecy_latest.json"
BTC_HOOK_DEFAULT = Path("projects/bitcoin-trading/memory/v2/ops/biblical_single_lane_trading_hook_v1_latest.json")
OUT_DEFAULT = ART / "prophecy_two_track_snapshot_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _summarize_track_a(prophecy: dict[str, Any], gate: dict[str, Any], btc_hook: dict[str, Any]) -> dict[str, Any]:
    gates = prophecy.get("gates") or {}
    st = gates.get("stability_gate") or {}
    op = prophecy.get("operator_brief") or {}
    lt = prophecy.get("live_trading") if isinstance(prophecy.get("live_trading"), dict) else {}
    out: dict[str, Any] = {
        "market": prophecy.get("market", "KOSPI"),
        "lane": prophecy.get("lane", "biblical_only"),
        "operator_brief": {
            "today_action": op.get("today_action"),
            "escalation": op.get("escalation"),
            "next_check_utc": op.get("next_check_utc"),
        },
        "gates_pass_snapshot": {
            "internal_gate_pass": bool((gates.get("internal_gate") or {}).get("pass")),
            "external_reality_gate_pass": bool((gates.get("external_reality_gate") or {}).get("pass")),
            "stability_go": bool(st.get("stability_go")),
            "ready_streak": st.get("ready_streak"),
            "streak_required": st.get("streak_required"),
        },
        "live_trading_hook": {
            "allowed": bool(lt.get("allowed", False)),
            "phase": lt.get("phase"),
        },
        "gate_stage": gate.get("stage"),
        "precommercial_ready": bool(gate.get("precommercial_ready", False)),
    }
    if btc_hook:
        out["bitcoin_hook"] = {
            "instrument": btc_hook.get("instrument"),
            "live_trading_allowed": bool((btc_hook.get("live_trading") or {}).get("allowed", False)),
        }
    return out


def _summarize_track_b(reg: dict[str, Any], path: Path) -> dict[str, Any]:
    if not reg:
        return {
            "registry_loaded": False,
            "artifact": str(path.as_posix()),
            "question_count": 0,
            "pending_resolution_count": 0,
        }
    questions = reg.get("questions") or []
    pending = 0
    for q in questions:
        res = q.get("resolution") or {}
        if str(res.get("status", "pending")).lower() == "pending":
            pending += 1
    return {
        "registry_loaded": True,
        "schema": reg.get("schema"),
        "research_rail": reg.get("research_rail"),
        "boundary_ack": reg.get("boundary_ack"),
        "artifact": str(path.as_posix()),
        "question_count": len(questions),
        "pending_resolution_count": pending,
        "omen_watch": {
            "intent": "Historical framing & forward-omen / sign detection (narrative layer).",
            "no_live_trigger": True,
            "eval_rail": "B-rail Tetlock-style; separate from Track A order path.",
        },
    }


def build(
    template: dict[str, Any],
    prophecy: dict[str, Any],
    gate: dict[str, Any],
    general: dict[str, Any],
    general_path: Path,
    btc_hook: dict[str, Any],
) -> dict[str, Any]:
    out = copy.deepcopy(template)
    out["generated_at_utc"] = _now_utc()
    fp = out.get("fusion_policy")
    if isinstance(fp, dict):
        fp.setdefault("auto_merge_to_live_trading", False)
        fp.setdefault("track_b_must_not_trigger_orders", True)
        fp.setdefault("track_b_for_live_execution", False)

    ta = out.get("track_a_trading_theory")
    if isinstance(ta, dict):
        ta["summary"] = _summarize_track_a(prophecy, gate, btc_hook)
        ta["evidence_paths"] = [
            {"name": "kospi_biblical_prophecy_output_v2", "path": str(PROPHECY_V2_DEFAULT.as_posix())},
            {"name": "kospi_biblical_single_lane_commercial_gate", "path": str(GATE_DEFAULT.as_posix())},
        ]
        if btc_hook:
            ta["evidence_paths"].append(
                {"name": "btc_biblical_hook", "path": str(BTC_HOOK_DEFAULT.as_posix())}
            )

    tb = out.get("track_b_historical_omen")
    if isinstance(tb, dict):
        tb["registry_summary"] = _summarize_track_b(general, general_path)
        tb["evidence_paths"] = [
            {"name": "general_prophecy_registry", "path": str(general_path.as_posix())},
        ]

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build prophecy two-track snapshot v1")
    ap.add_argument("--template", type=Path, default=TEMPLATE_DEFAULT)
    ap.add_argument("--prophecy-v2", type=Path, default=PROPHECY_V2_DEFAULT)
    ap.add_argument("--gate-json", type=Path, default=GATE_DEFAULT)
    ap.add_argument("--general-prophecy", type=Path, default=GENERAL_DEFAULT)
    ap.add_argument("--btc-hook", type=Path, default=BTC_HOOK_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    template = _load(args.template)
    if not template:
        print(json.dumps({"ok": False, "error": f"missing template: {args.template}"}, ensure_ascii=False))
        return 2

    prophecy = _load(args.prophecy_v2)
    gate = _load(args.gate_json)
    general = _load(args.general_prophecy)
    btc_hook = _load(args.btc_hook) if args.btc_hook.is_file() else {}

    snap = build(template, prophecy, gate, general, args.general_prophecy.resolve(), btc_hook)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
