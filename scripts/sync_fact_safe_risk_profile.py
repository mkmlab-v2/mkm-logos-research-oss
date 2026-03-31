"""Sync Fact-Safe prophecy risk profile into trader risk_profile_latest.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROPHECY = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
DEFAULT_OUT = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _derive_profile(risk_profile: dict[str, Any], now: datetime) -> dict[str, Any]:
    mode = str(risk_profile.get("mode") or "LOCKED_MODE").upper()
    core_decision = str(risk_profile.get("core_decision") or "HOLD").upper()
    core_score = float(risk_profile.get("core_score") or 0.0)
    core_contract_version = str(risk_profile.get("core_contract_version") or "unknown")
    position_scale_cap = float(risk_profile.get("position_scale_cap") or 0.2)
    daily_loss_cap_pct = float(risk_profile.get("daily_loss_cap_pct") or 1.0)
    fused_risk_pressure = float(risk_profile.get("fused_risk_pressure") or 0.8)
    core_decision_defined = "core_decision" in risk_profile
    force_hold = core_decision_defined and core_decision == "HOLD"

    if mode == "LOCKED_MODE" or force_hold:
        return {
            "schema_version": "risk_profile_v0.1",
            "generated_at": now.isoformat(timespec="seconds"),
            "expires_at": (now + timedelta(hours=12)).isoformat(timespec="seconds"),
            "source": "fact_safe_prophecy.trinity_governor",
            "mode": "shadow",
            "max_trades_per_day": 5,
            "max_position_size": 0.03,
            "maker_only_level": "strict",
            "slippage_cap_bps": 4,
            "kill_switch_threshold": 0.015,
            "trinity_governor": risk_profile,
            "singular_core": {
                "core_decision": core_decision,
                "core_score": core_score,
                "core_contract_version": core_contract_version,
            },
            "notes": "LOCKED_MODE enforced by Fact-Safe contract or singular core hold.",
        }

    max_trades = int(round(_clamp(40.0 * position_scale_cap, 10.0, 80.0)))
    max_position_size = round(_clamp(0.10 * position_scale_cap, 0.03, 0.20), 4)
    # High pressure -> tighter slippage bound.
    slippage_cap_bps = int(round(_clamp(12.0 - (fused_risk_pressure * 8.0), 3.0, 15.0)))
    kill_switch = round(_clamp(daily_loss_cap_pct / 100.0, 0.015, 0.04), 4)

    return {
        "schema_version": "risk_profile_v0.1",
        "generated_at": now.isoformat(timespec="seconds"),
        "expires_at": (now + timedelta(hours=12)).isoformat(timespec="seconds"),
        "source": "fact_safe_prophecy.trinity_governor",
        "mode": "shadow",
        "max_trades_per_day": max_trades,
        "max_position_size": max_position_size,
        "maker_only_level": "preferred",
        "slippage_cap_bps": slippage_cap_bps,
        "kill_switch_threshold": kill_switch,
        "trinity_governor": risk_profile,
        "singular_core": {
            "core_decision": core_decision,
            "core_score": core_score,
            "core_contract_version": core_contract_version,
        },
        "notes": "ACTIVE_MODE with trinity-governed risk clamp.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync Fact-Safe prophecy risk profile to trader risk profile.")
    ap.add_argument("--prophecy", default=str(DEFAULT_PROPHECY))
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    doc = _safe_json(Path(args.prophecy))
    risk_profile = doc.get("risk_profile") if isinstance(doc.get("risk_profile"), dict) else {}
    if not risk_profile:
        raise SystemExit("Missing risk_profile in prophecy artifact.")

    now = datetime.now(timezone.utc)
    out_doc = _derive_profile(risk_profile=risk_profile, now=now)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
