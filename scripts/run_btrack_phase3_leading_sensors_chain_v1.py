#!/usr/bin/env python3
"""Phase 3 B-track chain: leading-sensor stub ingest + human-review pack refresh (research_only).

LG-independent. Does not promote Track A or mutate prod ensemble score JSON.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/btrack_phase3_leading_sensors_manifest_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_phase3_leading_sensors_chain_v1_latest.json"
SCHEMA = "btrack_phase3_leading_sensors_chain_v1"

SEED_SCRIPT = ROOT / "scripts/seed_btrack_phase3_leading_sensors_stub_v1.py"
HR_PACK_SCRIPT = ROOT / "scripts/build_btrack_v1_price_only_human_review_pack_v1.py"
AUTO_OPT_SCRIPT = ROOT / "scripts/run_btrack_prophecy_auto_optimal_combo_v1.py"
JOIN_SCRIPT = ROOT / "scripts/join_btrack_phase3_leading_sensors_score_v1.py"
ABLATION_SCRIPT = ROOT / "scripts/run_btrack_phase3_leading_sensors_ablation_v1.py"
FETCH_BINANCE_SCRIPT = ROOT / "scripts/fetch_btrack_phase3_binance_micro_daily_v1.py"
FETCH_ONCHAIN_PROXY_SCRIPT = ROOT / "scripts/fetch_btrack_phase3_onchain_public_proxy_v1.py"
FEEDS_CHECK_SCRIPT = ROOT / "scripts/check_btrack_phase3_leading_sensor_feeds_v1.py"
SWEEP_SCRIPT = ROOT / "scripts/run_btrack_phase3_shield_threshold_sweep_v1.py"
SIZE_AUX_SCRIPT = ROOT / "scripts/run_btrack_phase3_size_confidence_aux_ablation_v1.py"
RETIREMENT_SCRIPT = ROOT / "scripts/build_btrack_phase3_shield_role_retirement_pack_v1.py"
LENS_PANEL_SCRIPT = ROOT / "scripts/build_btrack_multilens_per_date_lens_v1.py"
MULTILENS_AUX_SCRIPT = ROOT / "scripts/run_btrack_phase3_multilens_aux_eval_v1.py"
SIDECAR_SCRIPT = ROOT / "scripts/build_btrack_prophecy_score_insight_sidecar_stub_v1.py"
DEFAULT_SCORE_30 = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_SCORE_180 = ROOT / "reports/btrack_prophecy_score_recommended_180d_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd, cwd=str(ROOT))
    return int(p.returncode)


def _manifest_ok(manifest: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if manifest.get("schema") != "btrack_phase3_leading_sensors_manifest_v1":
        errs.append("schema_mismatch")
    sensors = manifest.get("sensors")
    if not isinstance(sensors, list) or not sensors:
        errs.append("sensors_empty")
    for s in sensors or []:
        if not isinstance(s, dict) or not s.get("sensor_id"):
            errs.append("sensor_missing_id")
    return errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--start", default="2025-08-01")
    ap.add_argument("--end", default="2026-05-17")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-seed", action="store_true")
    ap.add_argument(
        "--fetch-binance",
        action="store_true",
        help="Fetch Binance funding + long/short measured JSONL (network). Implies --skip-seed unless stub needed for onchain.",
    )
    ap.add_argument("--skip-feeds-check", action="store_true")
    ap.add_argument("--skip-auto-optimal", action="store_true")
    ap.add_argument("--skip-human-review-pack", action="store_true")
    ap.add_argument("--skip-join", action="store_true")
    ap.add_argument("--skip-ablation", action="store_true")
    ap.add_argument("--skip-shield-sweep", action="store_true")
    ap.add_argument("--skip-size-aux", action="store_true")
    ap.add_argument("--skip-lens-panel", action="store_true")
    ap.add_argument("--skip-multilens-aux-eval", action="store_true")
    ap.add_argument("--skip-sidecar-refresh", action="store_true")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_30)
    ap.add_argument("--join-180", action="store_true", help="Also join 180d recommended score if present.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.manifest.is_file():
        print(f"MISSING manifest: {args.manifest}", file=sys.stderr)
        return 2

    manifest = _load(args.manifest)
    m_errs = _manifest_ok(manifest)
    steps: list[dict[str, Any]] = []

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ok": m_errs == [],
                    "dry_run": True,
                    "manifest_errors": m_errs,
                    "sensors": [s.get("sensor_id") for s in manifest.get("sensors") or []],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if not m_errs else 1

    if m_errs:
        payload = {
            "schema": SCHEMA,
            "generated_at_utc": _utc_now(),
            "ok": False,
            "manifest_errors": m_errs,
            "steps": steps,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    if args.fetch_binance:
        code = _run([sys.executable, str(FETCH_BINANCE_SCRIPT)])
        steps.append({"step": "fetch_binance_micro_daily", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
        code = _run([sys.executable, str(FETCH_ONCHAIN_PROXY_SCRIPT)])
        steps.append({"step": "fetch_onchain_public_proxy", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_seed and not args.fetch_binance:
        code = _run(
            [
                sys.executable,
                str(SEED_SCRIPT),
                "--start",
                args.start,
                "--end",
                args.end,
                "--manifest",
                str(args.manifest),
            ]
        )
        steps.append({"step": "seed_leading_sensors_stub", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
    elif not args.skip_seed and args.fetch_binance:
        code = _run(
            [
                sys.executable,
                str(SEED_SCRIPT),
                "--start",
                args.start,
                "--end",
                args.end,
                "--manifest",
                str(args.manifest),
            ]
        )
        steps.append({"step": "seed_leading_sensors_stub_onchain_only", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_feeds_check:
        code = _run(
            [
                sys.executable,
                str(FEEDS_CHECK_SCRIPT),
                "--min-rows",
                "15",
                "--require-measured",
                "2" if args.fetch_binance else "0",
            ]
        )
        steps.append({"step": "check_leading_sensor_feeds", "exit_code": code})
        if code != 0 and args.fetch_binance:
            return _write_fail(args.output, steps)

    if not args.skip_auto_optimal:
        code = _run([sys.executable, str(AUTO_OPT_SCRIPT), "--include-180-fusion"])
        steps.append({"step": "auto_optimal_combo", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_human_review_pack:
        code = _run([sys.executable, str(HR_PACK_SCRIPT)])
        steps.append({"step": "human_review_pack_v1_price_only", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_join:
        code = _run(
            [
                sys.executable,
                str(JOIN_SCRIPT),
                "--score-json",
                str(args.score_json),
                "--instrument",
                "btc",
            ]
        )
        steps.append({"step": "join_leading_sensors_score_30d", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
        if args.join_180 and DEFAULT_SCORE_180.is_file():
            code180 = _run(
                [
                    sys.executable,
                    str(JOIN_SCRIPT),
                    "--score-json",
                    str(DEFAULT_SCORE_180),
                    "--instrument",
                    "btc",
                    "--out-jsonl",
                    str(ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.jsonl"),
                    "--out-meta",
                    str(ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.meta.json"),
                ]
            )
            steps.append({"step": "join_leading_sensors_score_180d", "exit_code": code180})
            if not args.skip_ablation:
                code_a180 = _run(
                    [
                        sys.executable,
                        str(ABLATION_SCRIPT),
                        "--joined-jsonl",
                        str(ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.jsonl"),
                        "--output",
                        str(ROOT / "reports/btrack_phase3_leading_sensors_ablation_180d_v1_latest.json"),
                    ]
                )
                steps.append({"step": "leading_sensors_ablation_180d", "exit_code": code_a180})

    if not args.skip_ablation:
        code = _run([sys.executable, str(ABLATION_SCRIPT)])
        steps.append({"step": "leading_sensors_ablation_30d", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_shield_sweep:
        code = _run([sys.executable, str(SWEEP_SCRIPT)])
        steps.append({"step": "shield_threshold_sweep", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_size_aux:
        code = _run(
            [
                sys.executable,
                str(SIZE_AUX_SCRIPT),
                "--window-label",
                "30d",
            ]
        )
        steps.append({"step": "size_confidence_aux_30d", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
        joined180 = ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.jsonl"
        if joined180.is_file():
            code = _run(
                [
                    sys.executable,
                    str(SIZE_AUX_SCRIPT),
                    "--joined-jsonl",
                    str(joined180),
                    "--output",
                    str(ROOT / "reports/btrack_phase3_size_confidence_aux_ablation_180d_v1_latest.json"),
                    "--window-label",
                    "180d",
                ]
            )
            steps.append({"step": "size_confidence_aux_180d", "exit_code": code})

    if not args.skip_shield_sweep:
        code = _run([sys.executable, str(RETIREMENT_SCRIPT)])
        steps.append({"step": "shield_role_retirement_pack", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    if not args.skip_lens_panel:
        code = _run(
            [
                sys.executable,
                str(LENS_PANEL_SCRIPT),
                "--score-json",
                str(args.score_json),
            ]
        )
        steps.append({"step": "multilens_per_date_loop_30d", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
        if args.join_180 and DEFAULT_SCORE_180.is_file():
            code = _run(
                [
                    sys.executable,
                    str(LENS_PANEL_SCRIPT),
                    "--score-json",
                    str(DEFAULT_SCORE_180),
                    "--output-json",
                    str(ROOT / "reports/btrack_multilens_per_date_lens_180d_v1_latest.json"),
                    "--output-jsonl",
                    str(ROOT / "reports/btrack_phase3_per_date_lens_panel_180d_v1_latest.jsonl"),
                    "--output-meta",
                    str(ROOT / "reports/btrack_phase3_per_date_lens_panel_180d_v1_latest.meta.json"),
                ]
            )
            steps.append({"step": "multilens_per_date_loop_180d", "exit_code": code})
            if code != 0:
                return _write_fail(args.output, steps)

    if not args.skip_multilens_aux_eval:
        code = _run([sys.executable, str(MULTILENS_AUX_SCRIPT)])
        steps.append({"step": "multilens_aux_eval_30d", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)
        joined180 = ROOT / "reports/btrack_phase3_leading_sensors_joined_180d_v1_latest.jsonl"
        panel180 = ROOT / "reports/btrack_phase3_per_date_lens_panel_180d_v1_latest.jsonl"
        if joined180.is_file() and panel180.is_file():
            code = _run(
                [
                    sys.executable,
                    str(MULTILENS_AUX_SCRIPT),
                    "--joined-jsonl",
                    str(joined180),
                    "--lens-panel-jsonl",
                    str(panel180),
                    "--output",
                    str(ROOT / "reports/btrack_phase3_multilens_aux_eval_180d_v1_latest.json"),
                    "--window-label",
                    "180d",
                ]
            )
            steps.append({"step": "multilens_aux_eval_180d", "exit_code": code})
            if code != 0:
                return _write_fail(args.output, steps)

    if not args.skip_sidecar_refresh:
        code = _run([sys.executable, str(SIDECAR_SCRIPT)])
        steps.append({"step": "insight_sidecar_refresh", "exit_code": code})
        if code != 0:
            return _write_fail(args.output, steps)

    hr_path = ROOT / "reports/btrack_v1_price_only_human_review_pack_v1_latest.json"
    hr_summary = None
    if hr_path.is_file():
        hr = _load(hr_path)
        hr_summary = {
            "human_decision": (hr.get("decision") or {}).get("human_decision"),
            "apply_to_prod": (hr.get("decision") or {}).get("apply_to_prod_score_json"),
            "prod_30d": (hr.get("metrics") or {}).get("prod_30d_hit_rate"),
            "cand_30d": (hr.get("metrics") or {}).get("candidate_30d_hit_rate"),
        }

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "lg_outcome_assumption": "independent_proceed_as_hold",
        "ok": True,
        "manifest": str(args.manifest.relative_to(ROOT)).replace("\\", "/"),
        "calendar_range": {"start": args.start, "end": args.end},
        "steps": steps,
        "human_review_pack_summary": hr_summary,
        "ablation_summary": _ablation_summary(),
        "feeds_check": _feeds_check_summary(),
        "shield_sweep_summary": _shield_sweep_summary(),
        "shield_retirement": _shield_retirement_summary(),
        "phase3_next_ko": [
            "onchain: Glassnode급 실측은 유료; 현재는 blockchain.info+Binance public proxy",
            "출생 프로필 기반 run_lens_* 실측 JSONL은 별도 체인",
        ],
        "operator_lines": [
            "- [MKM-PHASE3] track_a=OFF auto_promote=false",
            f"- [MKM-PHASE3] shield_retired={(_shield_retirement_summary() or {}).get('shield_as_direction_gate', 'n/a')}",
            f"- [MKM-PHASE3] hr_pack={hr_summary.get('human_decision') if hr_summary else 'n/a'}",
        ],
        "rerun": "py scripts/run_btrack_phase3_leading_sensors_chain_v1.py --fetch-binance --skip-auto-optimal",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


def _feeds_check_summary() -> dict[str, Any] | None:
    p = ROOT / "reports/btrack_phase3_leading_sensor_feeds_check_v1_latest.json"
    if not p.is_file():
        return None
    doc = _load(p)
    return {
        "ok": doc.get("ok"),
        "n_measured_sensors": doc.get("n_measured_sensors"),
        "sensors": doc.get("sensors"),
    }


def _shield_sweep_summary() -> dict[str, Any] | None:
    p = ROOT / "reports/btrack_phase3_shield_threshold_sweep_v1_latest.json"
    if not p.is_file():
        return None
    doc = _load(p)
    return {
        "shield_as_direction_gate": (doc.get("verdict") or {}).get("shield_as_direction_gate"),
        "windows": [
            {
                "window": w.get("window"),
                "baseline": (w.get("baseline") or {}).get("price_directional_hit_rate"),
                "best_shield": (w.get("best_shield") or {}).get("metrics", {}).get("price_directional_hit_rate"),
                "best_threshold": (w.get("best_shield") or {}).get("disagree_threshold"),
            }
            for w in doc.get("windows") or []
            if isinstance(w, dict)
        ],
    }


def _shield_retirement_summary() -> dict[str, Any] | None:
    p = ROOT / "reports/btrack_phase3_shield_role_retirement_pack_v1_latest.json"
    if not p.is_file():
        return None
    doc = _load(p)
    return doc.get("verdict")


def _ablation_summary() -> dict[str, Any] | None:
    p = ROOT / "reports/btrack_phase3_leading_sensors_ablation_v1_latest.json"
    if not p.is_file():
        return None
    doc = _load(p)
    profs = doc.get("profiles") or []
    out: dict[str, Any] = {}
    for row in profs:
        if isinstance(row, dict) and row.get("profile"):
            out[str(row["profile"])] = (row.get("metrics") or {}).get("price_directional_hit_rate")
    out["shield_uplift"] = (doc.get("verdict") or {}).get("shield_uplift_vs_baseline")
    return out


def _write_fail(out: Path, steps: list[dict[str, Any]]) -> int:
    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "ok": False,
        "steps": steps,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()} (failed)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
