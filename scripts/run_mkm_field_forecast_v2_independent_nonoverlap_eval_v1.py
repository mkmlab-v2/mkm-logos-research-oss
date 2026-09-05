#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run Field Forecast V2 independent non-overlap eval (reserved unseen only).

Requires COMMANDER_FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_ACK issued.
Does NOT overwrite Phase2/3 / broader qualification. ON_PASS: STOP. AUTO_NEXT=false.

  py scripts/run_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_field_forecast_v2_independent_nonoverlap_eval_core_v1 import (  # noqa: E402
    ACK_PATH,
    ACK_TOKEN,
    run_independent_nonoverlap_eval,
)

ART = ROOT / "docs/final/artifacts"
REP = ROOT / "reports"

FROZEN_FORBIDDEN_WRITE = [
    ART / "mkm_field_stock_forecast_v2_phase2_walkforward_latest.json",
    ART / "mkm_field_stock_forecast_v2_phase2_hashes_latest.json",
    ART / "mkm_field_stock_forecast_v2_phase3_qualification_latest.json",
    ART / "mkm_field_stock_forecast_v2_phase3_by_instrument_horizon_latest.json",
    ART / "mkm_field_stock_forecast_v2_phase3_hashes_latest.json",
    ART / "mkm_field_forecast_v2_dev_broader_panel_independent_requal_latest.json",
    ART / "mkm_field_forecast_v2_dev_independent_requal_qualification_latest.json",
    ART / "mkm_field_forecast_v2_dev_phase2_equivalent_refreeze_manifest_latest.json",
    REP / "mkm_field_stock_forecast_v2_phase2_prediction_raw_latest.jsonl",
    REP / "mkm_field_forecast_v2_dev_independent_requal_prediction_raw_latest.jsonl",
    REP / "mkm_field_forecast_v2_dev_smoke_prediction_raw_latest.jsonl",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, doc: object) -> None:
    if path.resolve() in {p.resolve() for p in FROZEN_FORBIDDEN_WRITE}:
        raise RuntimeError(f"REFUSING_WRITE_FROZEN: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    if path.resolve() in {p.resolve() for p in FROZEN_FORBIDDEN_WRITE}:
        raise RuntimeError(f"REFUSING_WRITE_FROZEN: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FSF V2 independent non-overlap eval")
    p.add_argument("--skip-ack-gate", action="store_true", help="tests only")
    p.add_argument("--out-dir-art", type=Path, default=ART)
    p.add_argument("--out-dir-rep", type=Path, default=REP)
    args = p.parse_args(argv)

    phase2 = ART / "mkm_field_stock_forecast_v2_phase2_walkforward_latest.json"
    phase3 = ART / "mkm_field_stock_forecast_v2_phase3_qualification_latest.json"
    broader = ART / "mkm_field_forecast_v2_dev_independent_requal_qualification_latest.json"
    before_phase2 = phase2.read_bytes() if phase2.is_file() else None
    before_phase3 = phase3.read_bytes() if phase3.is_file() else None
    before_broader = broader.read_bytes() if broader.is_file() else None

    if not args.skip_ack_gate:
        if not ACK_PATH.is_file():
            print(json.dumps({"ok": False, "error": "ACK_MISSING", "path": str(ACK_PATH)}))
            return 2
        ack = _load(ACK_PATH)
        aliases = set(ack.get("token_aliases") or [])
        token_ok = ack.get("token") == ACK_TOKEN or ACK_TOKEN in aliases
        if not ack.get("issued") or not token_ok:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "ACK_NOT_ISSUED",
                        "token": ack.get("token"),
                        "issued": ack.get("issued"),
                    },
                    ensure_ascii=False,
                )
            )
            return 2
        for key, expected in (
            ("research_only", True),
            ("live", False),
            ("auto_trade", False),
            ("AUTO_NEXT", False),
            ("on_pass", "STOP"),
        ):
            if ack.get(key) != expected:
                print(json.dumps({"ok": False, "error": f"ACK_{key}", "got": ack.get(key)}))
                return 2
        send = ack.get("send_gate") or ack.get("SEND")
        if send != "HOLD":
            print(json.dumps({"ok": False, "error": "ACK_SEND", "got": send}))
            return 2
        if ack.get("CORE_RULE") != "evaluate frozen system; do not improve frozen system":
            print(json.dumps({"ok": False, "error": "ACK_CORE_RULE", "got": ack.get("CORE_RULE")}))
            return 2
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
            if walls.get(wkey) is not True:
                print(json.dumps({"ok": False, "error": f"ACK_WALL_{wkey}"}))
                return 2
        if ack.get("ORACLE_SESSION_UPGRADE") != "FAIL":
            print(json.dumps({"ok": False, "error": "ACK_SESSION_UPGRADE_MUST_REMAIN_FAIL"}))
            return 2

    result = run_independent_nonoverlap_eval(root=ROOT)
    out = args.out_dir_art
    rep = args.out_dir_rep
    paths = {
        "prereg": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_prereg_manifest_latest.json",
        "freeze_verify": out
        / "mkm_field_forecast_v2_independent_nonoverlap_eval_frozen_input_hash_verify_latest.json",
        "nonoverlap_proof": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_nonoverlap_proof_latest.json",
        "prediction_raw": rep / "mkm_field_forecast_v2_independent_nonoverlap_eval_prediction_raw_latest.jsonl",
        "labels": rep / "mkm_field_forecast_v2_independent_nonoverlap_eval_labels_latest.jsonl",
        "qualification": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_qualification_latest.json",
        "baseline": out
        / "mkm_field_forecast_v2_independent_nonoverlap_eval_baseline_comparison_latest.json",
        "null_ci": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_null_ci_latest.json",
        "no_call": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_no_call_latest.json",
        "leakage": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_leakage_audit_latest.json",
        "stats": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_stats_latest.json",
        "hashes": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_hashes_latest.json",
        "summary": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_v1_latest.json",
        "receipt": out / "mkm_field_forecast_v2_independent_nonoverlap_eval_observed_result_receipt_v1.json",
    }

    if not result.get("ok"):
        fail_doc = {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_v1",
            "ok": False,
            "observed_result": "FAIL",
            "error": result.get("error"),
            "pipeline_sealed": True,
            "research_only": True,
            "send_gate": "HOLD",
            "live": False,
            "AUTO_NEXT": False,
            "on_pass": "STOP",
            "ORACLE_SESSION_UPGRADE": "FAIL",
            "freeze_verify": result.get("freeze_verify"),
            "nonoverlap_proof": result.get("nonoverlap_proof"),
            "window_meta": result.get("window_meta"),
        }
        _write(paths["summary"], fail_doc)
        if result.get("freeze_verify"):
            _write(paths["freeze_verify"], result["freeze_verify"])
        if result.get("nonoverlap_proof"):
            _write(paths["nonoverlap_proof"], result["nonoverlap_proof"])
        _write(
            paths["receipt"],
            {
                "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_observed_result_receipt_v1",
                "observed_result": "FAIL",
                "error": result.get("error"),
                "pipeline_sealed": True,
                "ORACLE_SESSION_UPGRADE": "FAIL",
                "research_only": True,
                "send_gate": "HOLD",
                "live": False,
                "AUTO_NEXT": False,
                "on_pass": "STOP",
            },
        )
        print(json.dumps({"ok": False, "observed_result": "FAIL", "error": result.get("error")}, ensure_ascii=False))
        return 2

    _write(paths["prereg"], result["prereg"])
    _write(paths["freeze_verify"], result["freeze_verify"])
    _write(paths["nonoverlap_proof"], result["nonoverlap_proof"])
    _write_jsonl(paths["prediction_raw"], result["prediction_rows"])
    _write_jsonl(paths["labels"], result["label_rows"])
    _write(paths["qualification"], result["qualification"])
    _write(paths["baseline"], result["baseline_comparison"])
    _write(paths["null_ci"], result["null_ci_report"])
    _write(paths["no_call"], result["no_call_report"])
    _write(paths["leakage"], result["leakage_audit"])
    _write(paths["stats"], result["stats"])

    hashes = dict(result["hashes"])
    hashes["prediction_raw_sha256"] = _sha256_file(paths["prediction_raw"])
    hashes["labels_sha256"] = _sha256_file(paths["labels"])
    hashes["qualification_sha256"] = _sha256_file(paths["qualification"])
    hashes["observed_result"] = result["summary"].get("observed_result")
    _write(paths["hashes"], hashes)

    summary = dict(result["summary"])
    summary["artifact_paths"] = {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in paths.items()}
    _write(paths["summary"], summary)

    wm = summary.get("window_meta") or {}
    receipt = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_observed_result_receipt_v1",
        "generated_at_utc": summary.get("generated_at_utc"),
        "observed_result": summary.get("observed_result"),
        "ALLOWED_RESULT": summary.get("ALLOWED_RESULT"),
        "insufficient_reason": summary.get("insufficient_reason"),
        "pipeline_sealed": True,
        "DECIDE_ONE": summary.get("DECIDE_ONE"),
        "pass_ceiling": summary.get("pass_ceiling"),
        "EVIDENCE_CEILING": summary.get("EVIDENCE_CEILING"),
        "window_label": summary.get("label"),
        "date_start": wm.get("date_start"),
        "date_end": wm.get("date_end"),
        "n_bars": wm.get("n_bars"),
        "selection_rule": wm.get("selection_rule"),
        "n_pred_rows": summary.get("n_pred_rows"),
        "zero_frozen_wf_folds": summary.get("zero_frozen_wf_folds"),
        "SIGNAL_CANDIDATE_count": summary.get("SIGNAL_CANDIDATE_count"),
        "SIGNAL_CANDIDATE_claimed": False,
        "MARKET_ALPHA_ESTABLISHED": False,
        "includes_3_lens": False,
        "tuning_after_results": False,
        "ORACLE_SESSION_UPGRADE": "FAIL",
        "session_upgrade_not_reinterpreted_as_pass": True,
        "browser_host_ok": True,
        "PASS_NE_PROFIT": True,
        "PASS_NE_GENERALIZATION": True,
        "PASS_NE_3_LENS_SUPERIORITY": True,
        "PASS_NE_TRADE": True,
        "research_only": True,
        "send_gate": "HOLD",
        "live": False,
        "AUTO_NEXT": False,
        "on_pass": "STOP",
        "git_commit_sha": summary.get("git_commit_sha"),
        "prediction_raw_sha256": hashes.get("prediction_raw_sha256"),
        "qualification_sha256": hashes.get("qualification_sha256"),
        "summary_path": str(paths["summary"].relative_to(ROOT)).replace("\\", "/"),
        "check_command": "py scripts/check_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py",
        "reproduce_command": "py scripts/run_mkm_field_forecast_v2_independent_nonoverlap_eval_v1.py",
    }
    _write(paths["receipt"], receipt)

    if before_phase2 is not None and phase2.read_bytes() != before_phase2:
        print(json.dumps({"ok": False, "error": "PHASE2_MUTATED"}))
        return 2
    if before_phase3 is not None and phase3.read_bytes() != before_phase3:
        print(json.dumps({"ok": False, "error": "PHASE3_MUTATED"}))
        return 2
    if before_broader is not None and broader.read_bytes() != before_broader:
        print(json.dumps({"ok": False, "error": "BROADER_QUAL_MUTATED"}))
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "observed_result": summary.get("observed_result"),
                "DECIDE_ONE": summary.get("DECIDE_ONE"),
                "pass_ceiling": summary.get("pass_ceiling"),
                "n_bars": wm.get("n_bars"),
                "n_pred_rows": summary.get("n_pred_rows"),
                "SIGNAL_CANDIDATE_count": summary.get("SIGNAL_CANDIDATE_count"),
                "ORACLE_SESSION_UPGRADE": "FAIL",
                "AUTO_NEXT": False,
                "on_pass": "STOP",
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
