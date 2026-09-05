#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checker for Field Forecast V2 independent non-overlap eval.

Exit 0 = sealed observed_result in {PASS, ZERO_CANDIDATE, INSUFFICIENT_DATA}
and contracts hold. Exit 2 otherwise (FAIL / missing / wall break).

  py scripts/check_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACK = ROOT / "docs/final/artifacts/commander_field_forecast_v2_independent_nonoverlap_eval_ack_v1.json"
SUMMARY = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_v1_latest.json"
RECEIPT = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_observed_result_receipt_v1.json"
PREREG = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_prereg_manifest_latest.json"
PROOF = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_nonoverlap_proof_latest.json"
QUAL = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_qualification_latest.json"
HASHES = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_hashes_latest.json"
PRED = ROOT / "reports/mkm_field_forecast_v2_independent_nonoverlap_eval_prediction_raw_latest.jsonl"
REPORT = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_independent_nonoverlap_eval_check_v1_latest.json"

PHASE2 = ROOT / "docs/final/artifacts/mkm_field_stock_forecast_v2_phase2_walkforward_latest.json"
PHASE3 = ROOT / "docs/final/artifacts/mkm_field_stock_forecast_v2_phase3_qualification_latest.json"

ACK_TOKEN = "COMMANDER_FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_ACK"
PASS_CEILING = "INDEPENDENT_NONOVERLAP_QUALIFICATION_ONLY"
DECIDE_OK = "FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_STRUCTURAL_OK"
ALLOWED = {"PASS", "ZERO_CANDIDATE", "INSUFFICIENT_DATA"}
QUAL_ENUM = {
    "SIGNAL_CANDIDATE",
    "WEAK_OR_UNSTABLE",
    "NO_INCREMENTAL_SIGNAL",
    "INSUFFICIENT_DATA",
    "CONFLICT_PRESENT",
}


def _pass(checks: list[dict[str, Any]], code: str, detail: str = "") -> None:
    checks.append({"ok": True, "code": code, "detail": detail})


def _fail(checks: list[dict[str, Any]], code: str, detail: str = "") -> None:
    checks.append({"ok": False, "code": code, "detail": detail})


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    checks: list[dict[str, Any]] = []
    required = {
        "ACK": ACK,
        "SUMMARY": SUMMARY,
        "RECEIPT": RECEIPT,
        "PHASE2": PHASE2,
        "PHASE3": PHASE3,
    }
    for name, path in required.items():
        if path.is_file():
            _pass(checks, f"FILE_{name}", path.name)
        else:
            _fail(checks, f"FILE_{name}_MISSING", str(path))

    if not ACK.is_file() or not SUMMARY.is_file() or not RECEIPT.is_file():
        doc = {"ok": False, "observed_result": "FAIL", "checks": checks, "error": "REQUIRED_MISSING"}
        REPORT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": "REQUIRED_MISSING"}, ensure_ascii=False))
        return 2

    ack = _load(ACK)
    summary = _load(SUMMARY)
    receipt = _load(RECEIPT)
    proof = _load(PROOF) if PROOF.is_file() else {}
    qual = _load(QUAL) if QUAL.is_file() else {}
    hashes = _load(HASHES) if HASHES.is_file() else {}
    prereg = _load(PREREG) if PREREG.is_file() else {}

    aliases = set(ack.get("token_aliases") or [])
    if ack.get("issued") is True and (ack.get("token") == ACK_TOKEN or ACK_TOKEN in aliases):
        _pass(checks, "ACK_ISSUED_TOKEN")
    else:
        _fail(checks, "ACK_ISSUED_TOKEN", str(ack.get("token")))

    if ack.get("ORACLE_SESSION_UPGRADE") == "FAIL" and summary.get("ORACLE_SESSION_UPGRADE") == "FAIL":
        _pass(checks, "SESSION_UPGRADE_REMAINS_FAIL")
    else:
        _fail(checks, "SESSION_UPGRADE_REMAINS_FAIL")

    for key, expected in (
        ("research_only", True),
        ("live", False),
        ("auto_trade", False),
        ("AUTO_NEXT", False),
        ("on_pass", "STOP"),
    ):
        if ack.get(key) == expected:
            _pass(checks, f"ACK_{key}")
        else:
            _fail(checks, f"ACK_{key}", str(ack.get(key)))
    send = ack.get("send_gate") or ack.get("SEND")
    if send == "HOLD":
        _pass(checks, "ACK_SEND_HOLD")
    else:
        _fail(checks, "ACK_SEND", str(send))

    walls = ack.get("walls") or {}
    for wkey in (
        "NO_OVERWRITE_PHASE2_FROZEN",
        "NO_OVERWRITE_PHASE3_FROZEN",
        "NO_3_LENS_IN_DEV_LANE",
        "NO_RETUNE",
        "NO_HISTORICAL_UNUSED_BACKFILL",
        "NO_SMOKE_DATA_REUSE",
        "SESSION_UPGRADE_FAIL_MUST_REMAIN_FAIL",
    ):
        if walls.get(wkey) is True:
            _pass(checks, f"ACK_WALL_{wkey}")
        else:
            _fail(checks, f"ACK_WALL_{wkey}", str(walls.get(wkey)))

    observed = summary.get("observed_result")
    if observed in ALLOWED and receipt.get("observed_result") == observed:
        _pass(checks, "OBSERVED_RESULT_SEALED", str(observed))
    else:
        _fail(checks, "OBSERVED_RESULT_SEALED", f"summary={observed} receipt={receipt.get('observed_result')}")

    if summary.get("pass_ceiling") == PASS_CEILING:
        _pass(checks, "PASS_CEILING")
    else:
        _fail(checks, "PASS_CEILING", str(summary.get("pass_ceiling")))

    if summary.get("DECIDE_ONE") == DECIDE_OK:
        _pass(checks, "DECIDE_OK")
    else:
        _fail(checks, "DECIDE_OK", str(summary.get("DECIDE_ONE")))

    wm = summary.get("window_meta") or {}
    if wm.get("selection_rule") == "reserved_future_unseen_only_no_historical_backfill":
        _pass(checks, "RESERVED_ONLY_RULE")
    else:
        _fail(checks, "RESERVED_ONLY_RULE", str(wm.get("selection_rule")))
    if str(wm.get("reserved_future_date_start") or "") == "2026-09-03":
        _pass(checks, "RESERVED_START_2026_09_03")
    else:
        _fail(checks, "RESERVED_START", str(wm.get("reserved_future_date_start")))
    if summary.get("label") == "independent_nonoverlap_reserved_future":
        _pass(checks, "WINDOW_LABEL")
    else:
        _fail(checks, "WINDOW_LABEL", str(summary.get("label")))

    ds = wm.get("date_start")
    if ds is None or str(ds) >= "2026-09-03":
        _pass(checks, "NO_PRE_RESERVED_EVAL_START", str(ds))
    else:
        _fail(checks, "NO_PRE_RESERVED_EVAL_START", str(ds))

    if proof.get("ok") is True:
        _pass(checks, "NONOVERLAP_PROOF_OK")
    else:
        _fail(checks, "NONOVERLAP_PROOF_OK", str(proof.get("fail_n")))

    for key, expected in (
        ("research_only", True),
        ("live", False),
        ("includes_3_lens", False),
        ("tuning_after_results", False),
        ("SIGNAL_CANDIDATE_claimed", False),
        ("MARKET_ALPHA_ESTABLISHED", False),
        ("AUTO_NEXT", False),
        ("on_pass", "STOP"),
        ("pipeline_sealed", True),
        ("PASS_NE_PROFIT", True),
        ("PASS_NE_TRADE", True),
    ):
        if summary.get(key) == expected:
            _pass(checks, f"SUMMARY_{key}")
        else:
            _fail(checks, f"SUMMARY_{key}", str(summary.get(key)))

    send_s = summary.get("send_gate") or summary.get("SEND")
    if send_s == "HOLD":
        _pass(checks, "SUMMARY_SEND_HOLD")
    else:
        _fail(checks, "SUMMARY_SEND", str(send_s))

    if observed == "INSUFFICIENT_DATA":
        if summary.get("zero_frozen_wf_folds") is True or int(summary.get("n_pred_rows") or 0) == 0:
            _pass(checks, "INSUFFICIENT_CONSISTENT")
        else:
            _fail(checks, "INSUFFICIENT_CONSISTENT", "labelled insufficient but folds/rows present")
    elif observed == "ZERO_CANDIDATE":
        if int(summary.get("SIGNAL_CANDIDATE_count") or 0) == 0:
            _pass(checks, "ZERO_CANDIDATE_CONSISTENT")
        else:
            _fail(checks, "ZERO_CANDIDATE_CONSISTENT")

    qtable = qual.get("qualification_table") or []
    if qtable:
        bad = [r for r in qtable if r.get("qualification_label") not in QUAL_ENUM]
        if not bad:
            _pass(checks, "QUAL_ENUM", f"n_cells={len(qtable)}")
        else:
            _fail(checks, "QUAL_ENUM", str(bad[:2]))
    elif observed == "INSUFFICIENT_DATA":
        _pass(checks, "QUAL_TABLE_OPTIONAL_WHEN_INSUFFICIENT")
    else:
        _fail(checks, "QUAL_TABLE_EMPTY")

    if PRED.is_file():
        _pass(checks, "PRED_FILE")
        for line in PRED.read_text(encoding="utf-8").splitlines()[:20]:
            if not line.strip():
                continue
            row = json.loads(line)
            asof = str(row.get("asof_date") or "")[:10]
            if asof and asof < "2026-09-03":
                _fail(checks, "PRED_ASOF_PRE_RESERVED", asof)
                break
        else:
            _pass(checks, "PRED_ASOF_RESERVED_ONLY")
    elif observed == "INSUFFICIENT_DATA":
        _pass(checks, "PRED_OPTIONAL_WHEN_INSUFFICIENT")
    else:
        _fail(checks, "PRED_MISSING")

    if hashes.get("observed_result") in (None, observed):
        _pass(checks, "HASHES_OBSERVED")
    else:
        _fail(checks, "HASHES_OBSERVED", str(hashes.get("observed_result")))

    if prereg.get("lens_wall", {}).get("three_lens") is False:
        _pass(checks, "PREREG_NO_3_LENS")
    elif observed == "INSUFFICIENT_DATA" and not prereg:
        _pass(checks, "PREREG_OPTIONAL_WHEN_INSUFFICIENT")
    else:
        _fail(checks, "PREREG_NO_3_LENS")

    fail_n = sum(1 for c in checks if not c["ok"])
    ok = fail_n == 0
    report = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_check_v1",
        "ok": ok,
        "observed_result": observed if ok else "FAIL",
        "DECIDE_ONE": DECIDE_OK if ok else "FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_CHECK_FAIL",
        "fail_n": fail_n,
        "pass_ceiling": PASS_CEILING,
        "EVIDENCE_CEILING": PASS_CEILING,
        "ORACLE_SESSION_UPGRADE": "FAIL",
        "AUTO_NEXT": False,
        "CORE_RULE": "evaluate frozen system; do not improve frozen system",
        "checks": checks,
        "paths": {
            "ack": str(ACK).replace("\\", "/"),
            "summary": str(SUMMARY).replace("\\", "/"),
            "receipt": str(RECEIPT).replace("\\", "/"),
        },
        "check_command": "py scripts/check_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py",
        "lane": "oracle",
        "research_only": True,
        "send_gate": "HOLD",
        "live": False,
        "SIGNAL_CANDIDATE_claimed": False,
        "MARKET_ALPHA_ESTABLISHED": False,
        "on_pass": "STOP",
        "next_requires_separate_ack": "COMMANDER_FIELD_FORECAST_V2_MORE_UNSEEN_OR_HISTORICAL_REDESIGN_ACK",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok,
                "observed_result": report["observed_result"],
                "fail_n": fail_n,
                "ORACLE_SESSION_UPGRADE": "FAIL",
                "on_pass": "STOP",
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
