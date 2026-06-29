#!/usr/bin/env python3
"""[HYPO] Phase 0 observe-only readiness for B-track Type-A guard — no live trading enable."""
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

SCHEMA = "btrack_phase0_observe_only_readiness_v1"
APPROVAL = ROOT / "docs/final/artifacts/btrack_btc_typea_guard_human_approval_v1_latest.json"
SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
HIT_RATE = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
ENV_FILE = ROOT / ".env"
BT_CFG = ROOT / "projects/bitcoin-trading/config/trading_config.yaml"
DEFAULT_OUT = ROOT / "reports/btrack_phase0_observe_only_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_bool(raw: str | None, default: bool) -> tuple[bool, bool]:
    """Return (value, parsed_ok)."""
    if raw is None or not str(raw).strip():
        return default, False
    s = str(raw).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True, True
    if s in ("0", "false", "no", "n", "off"):
        return False, True
    return default, False


def _dotenv_keys(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if "=" not in t:
            continue
        k, v = t.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _yaml_scalar(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    import re

    pat = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.+)\s*$")
    last: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m:
            last = m.group(1).strip()
    return last


def build_status(*, strict: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            blockers.append(f"{name}: {detail}")

    approval_ok = False
    approval_decision = None
    if APPROVAL.is_file():
        apv = _load(APPROVAL)
        approval_decision = apv.get("decision")
        approval_ok = str(approval_decision) == "APPROVED_BTC_TYPEA_GUARD_OPERATIONAL_SCORE"
    add("typea_guard_human_approval", approval_ok, str(approval_decision or "missing"))

    guard_meta_ok = False
    guard_applied_rows = 0
    if SCORE.is_file():
        score = _load(SCORE)
        meta = score.get("meta") or {}
        guard_meta = meta.get("btc_typea_guard_v1") if isinstance(meta, dict) else None
        guard_meta_ok = isinstance(guard_meta, dict) and bool(guard_meta.get("policy_id"))
        for row in score.get("rows") or []:
            if isinstance(row, dict) and str(row.get("instrument")).lower() == "btc":
                if row.get("typea_guard_applied"):
                    guard_applied_rows += 1
    add(
        "operational_score_guard_meta",
        guard_meta_ok,
        f"guard_meta={guard_meta_ok} applied_btc_rows={guard_applied_rows}",
    )

    dual_ok = DUAL.is_file()
    add("dual_per_date_directions", dual_ok, str(DUAL))

    hit_btc = None
    if HIT_RATE.is_file():
        hr = _load(HIT_RATE)
        metrics = hr.get("metrics") or {}
        if isinstance(metrics, dict) and metrics.get("price_directional_hit_rate") is not None:
            hit_btc = metrics.get("price_directional_hit_rate")
        else:
            inst = hr.get("by_instrument") or {}
            btc = inst.get("btc") if isinstance(inst, dict) else None
            if isinstance(btc, dict):
                hit_btc = btc.get("price_directional_hit_rate")
    add("prophecy_hit_rate_headline", HIT_RATE.is_file(), f"btc_hit_rate={hit_btc}")

    env = _dotenv_keys(ENV_FILE)
    cfg_testnet_raw = _yaml_scalar(BT_CFG, "testnet")
    cfg_enable_live = _yaml_scalar(BT_CFG, "enable_live_trading")
    cfg_enable = _yaml_scalar(BT_CFG, "enable_trading")
    cfg_enable_raw = cfg_enable_live or cfg_enable
    cfg_testnet, _ = _parse_bool(cfg_testnet_raw, True)
    cfg_enable_trading, _ = _parse_bool(cfg_enable_raw, False)
    et_raw = env.get("ENABLE_TRADING")
    tn_raw = env.get("TESTNET")
    effective_enable, _ = _parse_bool(et_raw, cfg_enable_trading)
    effective_testnet, _ = _parse_bool(tn_raw, cfg_testnet)

    observe_only = not effective_enable
    add(
        "observe_only_trading_disabled",
        observe_only,
        f"effective_enable_trading={effective_enable} effective_testnet={effective_testnet}",
    )

    daily_chain_hook = (ROOT / "scripts/run_btrack_daily_hypothesis_chain.ps1").is_file()
    add("daily_chain_typea_hook_present", daily_chain_hook, "run_btrack_daily_hypothesis_chain.ps1")

    phase0_ready = approval_ok and guard_meta_ok and dual_ok and observe_only
    guard_pipeline_ready = approval_ok and guard_meta_ok and dual_ok and daily_chain_hook
    if strict and not phase0_ready:
        raise SystemExit(f"phase0 not ready: {'; '.join(blockers)}")

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "guard_pipeline_ready": guard_pipeline_ready,
        "phase0_observe_only_ready": phase0_ready,
        "live_trading_enabled": effective_enable,
        "track_a_auto_promote": False,
        "combined_all_passed": False,
        "effective_trading_profile": {
            "enable_trading": effective_enable,
            "testnet": effective_testnet,
            "observe_only": observe_only,
        },
        "btc_headline_hit_rate": hit_btc,
        "guard_applied_btc_rows": guard_applied_rows,
        "checks": checks,
        "blockers": blockers,
        "next_recommended": (
            "Phase 0: run daily chain + post-close ingest; monitor score/guard artifacts only."
            if phase0_ready
            else (
                "Guard pipeline OK; set ENABLE_TRADING=0 for observe-only Phase 0, or proceed to Phase 1 micro-live with explicit caps."
                if guard_pipeline_ready
                else "Resolve blockers before Phase 1 micro-live experiment."
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when phase0_observe_only_ready is false.")
    args = ap.parse_args(argv)

    doc = build_status(strict=args.strict)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"phase0_observe_only_ready={doc['phase0_observe_only_ready']}")
    print(f"guard_pipeline_ready={doc.get('guard_pipeline_ready')}")
    if doc["blockers"]:
        print("blockers:", "; ".join(doc["blockers"]))
    return 0 if doc["phase0_observe_only_ready"] else (1 if args.strict else 0)


if __name__ == "__main__":
    raise SystemExit(main())
