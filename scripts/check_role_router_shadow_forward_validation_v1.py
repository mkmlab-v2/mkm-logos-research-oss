#!/usr/bin/env python3
"""Evaluate shadow-forward validation gate and emit promotion decision receipt.

Reads role_router_shadow_forward_validation_gate_v1 JSON and compares:
- required artifact checks (preflight/intent/observer/watchdog/breaker)
- BTC/KOSPI threshold blocks from optimizer outputs
- cross-asset guardrail integrity

Writes:
- reports/role_router_shadow_forward_validation_decision_latest.json
- reports/role_router_shadow_forward_validation_decision_log.jsonl
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "role_router_shadow_forward_validation_gate_v1.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _parse_ts(ts: str) -> datetime | None:
    s = str(ts or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def _resolve_path(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def _check_artifact_pass(check_id: str, artifact_path: Path, min_window_start: datetime) -> tuple[bool, str]:
    if check_id == "CHECK_01_ENGINE_CONTRACT":
        doc = _load_json(artifact_path)
        if not doc:
            return False, "missing_or_invalid_json"
        return (str(doc.get("result") or "") == "PASS"), str(doc.get("result") or "missing_result")

    if check_id == "CHECK_02_INTENT_CONTRACT":
        doc = _load_json(artifact_path)
        if not doc:
            return False, "missing_or_invalid_json"
        return (str(doc.get("result") or "") == "PASS"), str(doc.get("result") or "missing_result")

    if check_id == "CHECK_03_FIRST30M_OBSERVER":
        doc = _load_json(artifact_path)
        if not doc:
            return False, "missing_or_invalid_json"
        ok = str(doc.get("result") or "") == "PASS" and not (doc.get("fail_conditions") or [])
        return ok, str(doc.get("result") or "missing_result")

    if check_id == "CHECK_04_24H_WATCHDOG_HEALTH":
        rows = _read_jsonl(artifact_path)
        if not rows:
            return False, "missing_or_empty_jsonl"
        recent = []
        for r in rows:
            ts = _parse_ts(str(r.get("ts_utc") or ""))
            if ts and ts >= min_window_start:
                recent.append(r)
        if not recent:
            return False, "no_rows_in_window"
        bad = [r for r in recent if bool(r.get("healthy")) is False]
        return (len(bad) == 0), f"recent_rows={len(recent)} unhealthy_rows={len(bad)}"

    if check_id == "CHECK_05_CIRCUIT_BREAKER_REHEARSAL":
        doc = _load_json(artifact_path)
        if not doc:
            return False, "missing_or_invalid_json"
        return (str(doc.get("result") or "") == "PASS"), str(doc.get("result") or "missing_result")

    return False, "unknown_check_id"


def _threshold_block_pass(doc: dict[str, Any], cfg: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    best = doc.get("best_candidate") or {}
    best_oos_days = int(best.get("oos_days") or 0)
    oos = best.get("oos_metrics") or {}
    required_oos_days = cfg.get("required_oos_days")
    checks = {
        "required_oos_days": (required_oos_days is None) or (best_oos_days == int(required_oos_days)),
        "min_active_days": int(oos.get("n_active_days") or 0) >= int(cfg.get("min_active_days") or 0),
        "min_hit_rate_active": float(oos.get("directional_hit_rate_active") or 0.0) >= float(cfg.get("min_hit_rate_active") or 0.0),
        "min_total_return": float(oos.get("total_return") or 0.0) >= float(cfg.get("min_total_return") or 0.0),
        "max_mdd": float(oos.get("mdd") or 0.0) >= float(cfg.get("max_mdd") or -1.0),
        "min_sharpe": float(oos.get("sharpe") or 0.0) >= float(cfg.get("min_sharpe") or 0.0),
    }
    return all(checks.values()), {
        "checks": checks,
        "oos_days": best_oos_days,
        "required_oos_days": required_oos_days,
        "oos_metrics": oos,
        "params": best.get("params"),
        "robust_score": best.get("robust_score"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    args = ap.parse_args()

    gate = _load_json(args.gate_json)
    if not gate:
        raise SystemExit(f"invalid gate json: {args.gate_json}")

    now = _now_utc()
    min_days = int(((gate.get("window_policy") or {}).get("shadow_forward_min_days")) or 14)
    window_start = now - timedelta(days=min_days)

    # 1) Mandatory artifact checks
    check_results: list[dict[str, Any]] = []
    checks_passed = True
    for c in (gate.get("must_pass_checks") or []):
        cid = str(c.get("id") or "")
        aref = str(c.get("artifact_ref") or "")
        apath = _resolve_path(aref)
        ok, detail = _check_artifact_pass(cid, apath, window_start)
        check_results.append(
            {
                "id": cid,
                "artifact_ref": aref,
                "artifact_exists": apath.is_file(),
                "pass": ok,
                "detail": detail,
            }
        )
        checks_passed = checks_passed and ok

    # 2) Threshold checks from optimizer refs
    runtime = gate.get("target_runtime") or {}
    refs = runtime.get("optimizer_refs") or []
    btc_doc = None
    kospi_doc = None
    for ref in refs:
        p = _resolve_path(str(ref))
        d = _load_json(p)
        if not d:
            continue
        inst = str(((d.get("inputs") or {}).get("target_instrument")) or "").lower()
        if inst == "btc":
            btc_doc = d
        elif inst == "kospi":
            kospi_doc = d

    th = gate.get("promotion_gate_thresholds") or {}
    required_oos_days = th.get("required_oos_days")
    btc_ok, btc_detail = (False, {"error": "missing_btc_optimizer_ref"})
    if btc_doc:
        btc_cfg = dict(th.get("btc") or {})
        if required_oos_days is not None:
            btc_cfg["required_oos_days"] = required_oos_days
        btc_ok, btc_detail = _threshold_block_pass(btc_doc, btc_cfg)

    kospi_ok, kospi_detail = (False, {"error": "missing_kospi_optimizer_ref"})
    if kospi_doc:
        kospi_cfg = dict(th.get("kospi") or {})
        if required_oos_days is not None:
            kospi_cfg["required_oos_days"] = required_oos_days
        kospi_ok, kospi_detail = _threshold_block_pass(kospi_doc, kospi_cfg)

    # 3) Cross-asset safety (guardrail integrity-oriented)
    safety_cfg = th.get("cross_asset_safety") or {}
    engine_doc = _load_json(_resolve_path(str((runtime.get("engine_input_ref") or ""))))
    max_losses_ok = False
    if engine_doc:
        eng = engine_doc.get("engine_input") or {}
        max_losses_ok = int(eng.get("max_consecutive_losses") or 999) <= int(safety_cfg.get("max_consecutive_losses") or 999)
    breaker_pass = any((r.get("id") == "CHECK_05_CIRCUIT_BREAKER_REHEARSAL" and r.get("pass")) for r in check_results)
    guardrail_integrity_ok = bool(safety_cfg.get("require_guardrail_integrity")) is False or (max_losses_ok and breaker_pass)
    cross_asset_ok = max_losses_ok and guardrail_integrity_ok
    cross_asset_detail = {
        "max_consecutive_losses_ok": max_losses_ok,
        "guardrail_integrity_ok": guardrail_integrity_ok,
        "note": "max_any_single_day_loss_pct requires dedicated realized PnL log; not directly computed in this evaluator.",
    }

    thresholds_passed = btc_ok and kospi_ok and cross_asset_ok
    final_decision = "GO_LIVE_CANDIDATE" if (checks_passed and thresholds_passed) else "HOLD_SHADOW_ONLY"
    failed_reasons: list[str] = []
    if not checks_passed:
        failed_reasons.append("mandatory_checks_failed")
    if not btc_ok:
        failed_reasons.append("btc_threshold_block_failed")
    if not kospi_ok:
        failed_reasons.append("kospi_threshold_block_failed")
    if not cross_asset_ok:
        failed_reasons.append("cross_asset_safety_failed")

    receipt = {
        "schema": "role_router_shadow_forward_validation_decision_v1",
        "ts_utc": _iso(now),
        "window_start_utc": _iso(window_start),
        "window_end_utc": _iso(now),
        "gate_ref": str(args.gate_json),
        "checks_passed": checks_passed,
        "thresholds_passed": thresholds_passed,
        "final_decision": final_decision,
        "failed_reasons": failed_reasons,
        "details": {
            "mandatory_checks": check_results,
            "btc_threshold_block": {"pass": btc_ok, **btc_detail},
            "kospi_threshold_block": {"pass": kospi_ok, **kospi_detail},
            "cross_asset_safety": {"pass": cross_asset_ok, **cross_asset_detail},
        },
    }

    audit = gate.get("audit_contract") or {}
    out_latest = _resolve_path(str(audit.get("decision_receipt_out") or "reports/role_router_shadow_forward_validation_decision_latest.json"))
    out_log = _resolve_path(str(audit.get("decision_audit_log") or "reports/role_router_shadow_forward_validation_decision_log.jsonl"))
    out_latest.parent.mkdir(parents=True, exist_ok=True)
    out_log.parent.mkdir(parents=True, exist_ok=True)
    out_latest.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with out_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, ensure_ascii=False) + "\n")

    print(f"WROTE: {out_latest}")
    print(f"AUDIT_APPEND: {out_log}")
    print(f"final_decision={final_decision}")
    return 0 if final_decision == "GO_LIVE_CANDIDATE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

