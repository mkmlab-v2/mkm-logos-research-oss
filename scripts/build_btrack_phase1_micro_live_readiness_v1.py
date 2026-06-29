#!/usr/bin/env python3
"""[HYPO] Phase 1 micro-live experiment readiness (test account; not Track A promote)."""
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

from scripts.build_btrack_phase0_observe_only_status_v1 import _dotenv_keys, _parse_bool, _yaml_scalar

SCHEMA = "btrack_phase1_micro_live_readiness_v1"
MICRO_APPROVAL = ROOT / "docs/final/artifacts/btrack_btc_typea_micro_live_human_approval_v1_latest.json"
TYPEA_APPROVAL = ROOT / "docs/final/artifacts/btrack_btc_typea_guard_human_approval_v1_latest.json"
ENGINE_INPUT = ROOT / "docs/final/artifacts/btc_limited_live_engine_input_from_btrack_typea_v1_latest.json"
DIGEST = ROOT / "reports/btrack_phase1_micro_live_evolution_digest_v1_latest.json"
ROLLBACK = ROOT / "docs/final/artifacts/prophecy_live_rollback_policy_v1_latest.json"
BT_CFG = ROOT / "projects/bitcoin-trading/config/trading_config.yaml"
ENV_FILE = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/btrack_phase1_micro_live_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def build_status(*, strict: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            blockers.append(f"{name}: {detail}")

    micro = _load(MICRO_APPROVAL)
    typea = _load(TYPEA_APPROVAL)
    engine = _load(ENGINE_INPUT)
    digest = _load(DIGEST)
    rollback = _load(ROLLBACK)

    micro_ok = str(micro.get("decision") or "") == "APPROVED_BTRACK_TYPEA_MICRO_LIVE_EXPERIMENT"
    typea_ok = str(typea.get("decision") or "") == "APPROVED_BTC_TYPEA_GUARD_OPERATIONAL_SCORE"
    add("micro_live_human_approval", micro_ok, str(micro.get("decision") or "missing"))
    add("typea_guard_human_approval", typea_ok, str(typea.get("decision") or "missing"))

    engine_ready = str(engine.get("status") or "").upper() == "READY_FOR_ENGINE_SUBMIT"
    side = ((engine.get("btrack_signal") or {}).get("side_hint") or "HOLD")
    add("engine_handoff_ready", engine_ready, f"status={engine.get('status')} side_hint={side}")

    add("rollback_policy", str(rollback.get("schema") or "") == "prophecy_live_rollback_policy_v1", rollback.get("schema", "missing"))
    add("evolution_digest", bool(digest.get("schema")), str(DIGEST))

    overlay_py = ROOT / "projects/bitcoin-trading/src/futures_engine/btrack_typea_micro_live_overlay_v1.py"
    guard_py = ROOT / "projects/bitcoin-trading/src/futures_engine/btrack_typea_micro_live_guard_v1.py"
    add("aroon_btrack_overlay_module", overlay_py.is_file(), str(overlay_py.relative_to(ROOT)))
    add("aroon_btrack_policy_guard_module", guard_py.is_file(), str(guard_py.relative_to(ROOT)))

    env = _dotenv_keys(ENV_FILE)
    cfg_enable_raw = _yaml_scalar(BT_CFG, "enable_live_trading") or _yaml_scalar(BT_CFG, "enable_trading")
    cfg_testnet_raw = _yaml_scalar(BT_CFG, "testnet")
    cfg_enable, _ = _parse_bool(cfg_enable_raw, False)
    cfg_testnet, _ = _parse_bool(cfg_testnet_raw, True)
    effective_enable, _ = _parse_bool(env.get("ENABLE_TRADING"), cfg_enable)
    effective_testnet, _ = _parse_bool(env.get("TESTNET"), cfg_testnet)
    trading_armed = effective_enable and side in {"BUY", "SELL"}
    add(
        "trading_profile_armed",
        trading_armed,
        f"enable_trading={effective_enable} testnet={effective_testnet} side_hint={side}",
    )

    phase1_ready = micro_ok and typea_ok and engine_ready and rollback.get("schema") and trading_armed
    if strict and not phase1_ready:
        raise SystemExit(f"phase1 not ready: {'; '.join(blockers)}")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "phase1_micro_live_ready": bool(phase1_ready),
        "live_trading_enabled": effective_enable,
        "track_a_auto_promote": False,
        "combined_all_passed": False,
        "effective_trading_profile": {
            "enable_trading": effective_enable,
            "testnet": effective_testnet,
        },
        "engine_handoff": {
            "path": str(ENGINE_INPUT.relative_to(ROOT)),
            "status": engine.get("status"),
            "side_hint": side,
            "eval_date": (engine.get("btrack_signal") or {}).get("eval_date"),
            "size_usd": (engine.get("engine_input") or {}).get("size_usd"),
        },
        "digest_hit_rate": ((digest.get("btc_panel") or {}).get("hit_rate")),
        "checks": checks,
        "blockers": blockers,
        "next_recommended": (
            "Micro-live armed: Aroon=cross trigger, B-track=filter-only. "
            "Daily: Invoke-BtrackPhase1MicroLiveOpsRoutine_v1.ps1 or Register-BtrackPhase1MicroLiveDailySyncTask.ps1"
            if phase1_ready
            else "Complete blockers then re-run Invoke-BtrackPhase1MicroLiveExperiment_v1.ps1"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    doc = build_status(strict=args.strict)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"phase1_micro_live_ready={doc['phase1_micro_live_ready']}")
    if doc["blockers"]:
        print("blockers:", "; ".join(doc["blockers"]))
    return 0 if doc["phase1_micro_live_ready"] else (1 if args.strict else 0)


if __name__ == "__main__":
    raise SystemExit(main())
