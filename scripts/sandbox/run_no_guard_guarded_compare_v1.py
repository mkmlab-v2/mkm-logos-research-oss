#!/usr/bin/env python3
"""[HYPO] Compare No-Guard stress lane vs proxy-aligned guarded coding bench on same cases."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX = ROOT / "experiments" / "no_guard_limit_test"
DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1_n20.jsonl"
DEFAULT_NO_GUARD_PROFILE = SANDBOX / "no_guard_profile_v1.json"
DEFAULT_GUARDED_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
DEFAULT_OUT = SANDBOX / "results" / "no_guard_vs_guarded_compare_v1_latest.json"

CIRCUIT_BREAKER_MIN = 0.75


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text") is not None:
            rows.append(row)
    return rows


def _run_no_guard_case(
    text: str,
    *,
    lane: str | None,
    profile_path: Path,
) -> dict[str, Any]:
    from scripts.sandbox.run_no_guard_limit_stress_test_v1 import _eval_no_guard

    doc = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    lane_intensity = doc.get("lane_intensity") if isinstance(doc.get("lane_intensity"), dict) else {}
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(profile_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    m = _eval_no_guard(text, lane=lane, lane_intensity=lane_intensity, must_keep_extra=set())
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": m.get("reconstruction_fidelity_jaccard"),
        "proxy_path": m.get("proxy_path"),
        "scenario": m.get("scenario"),
        "elapsed_ms": m.get("elapsed_ms"),
        "circuit_breaker_would_fire": False,
    }


def _run_guarded_case(
    text: str,
    *,
    lane: str | None,
    hardening_path: Path,
) -> dict[str, Any]:
    from scripts.run_cursor_coding_compress_bench_v1 import (
        _eval_proxy_aligned,
        _load_lane_intensity,
        _selected_profile,
        _token_in,
    )

    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path)
    m = _eval_proxy_aligned(
        text, profile, lane=lane, lane_intensity=lane_intensity
    )
    jac = m.get("reconstruction_fidelity_jaccard")
    cb_fire = (
        m.get("proxy_path") == "circuit_break_identity"
        or (
            jac is not None
            and float(jac) < CIRCUIT_BREAKER_MIN
            and m.get("proxy_path") == "live_compress"
        )
    )
    return {
        "token_saving_rate": m.get("global_token_saving_rate"),
        "reconstruction_fidelity_jaccard": jac,
        "proxy_path": m.get("proxy_path"),
        "elapsed_ms": None,
        "circuit_breaker_would_fire": cb_fire,
        "circuit_break_reasons": m.get("circuit_break_reasons"),
    }


def run_compare(
    input_path: Path,
    *,
    no_guard_profile: Path,
    guarded_hardening: Path,
    dry_run: bool,
    max_cases: int,
) -> dict[str, Any]:
    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    if dry_run:
        return {
            "schema": "no_guard_vs_guarded_compare_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "hypothesis_tier": "B",
            "dry_run": True,
            "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "case_count": len(cases_in),
            "boundary_ack": "Dry-run only.",
        }

    rows: list[dict[str, Any]] = []
    cb_saved_count = 0
    bypass_only_count = 0

    for item in cases_in:
        raw = str(item["raw_text"])
        lane = item.get("lane")
        lane_s = str(lane) if lane else None
        ng = _run_no_guard_case(raw, lane=lane_s, profile_path=no_guard_profile)
        gd = _run_guarded_case(raw, lane=lane_s, hardening_path=guarded_hardening)

        ng_jac = ng.get("reconstruction_fidelity_jaccard")
        gd_jac = gd.get("reconstruction_fidelity_jaccard")
        delta_jac = None
        if ng_jac is not None and gd_jac is not None:
            delta_jac = float(gd_jac) - float(ng_jac)

        cb_saved = (
            gd.get("proxy_path") == "circuit_break_identity"
            and ng_jac is not None
            and float(ng_jac) < CIRCUIT_BREAKER_MIN
        )
        if cb_saved:
            cb_saved_count += 1
        if gd.get("proxy_path") == "gatekeeper_bypass":
            bypass_only_count += 1

        rows.append(
            {
                "id": item.get("id"),
                "lane": lane,
                "no_guard": ng,
                "guarded": gd,
                "delta_jaccard_guarded_minus_no_guard": delta_jac,
                "circuit_breaker_saved_quality": cb_saved,
            }
        )

    ng_jacs = [
        r["no_guard"]["reconstruction_fidelity_jaccard"]
        for r in rows
        if r["no_guard"].get("reconstruction_fidelity_jaccard") is not None
    ]
    gd_jacs = [
        r["guarded"]["reconstruction_fidelity_jaccard"]
        for r in rows
        if r["guarded"].get("reconstruction_fidelity_jaccard") is not None
    ]

    return {
        "schema": "no_guard_vs_guarded_compare_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "no_guard_profile": str(no_guard_profile.relative_to(ROOT)).replace("\\", "/"),
        "guarded_hardening": str(guarded_hardening.relative_to(ROOT)).replace("\\", "/"),
        "case_count": len(rows),
        "aggregate": {
            "circuit_breaker_saved_quality_count": cb_saved_count,
            "gatekeeper_bypass_count": bypass_only_count,
            "no_guard_avg_jaccard": sum(ng_jacs) / len(ng_jacs) if ng_jacs else None,
            "guarded_avg_jaccard": sum(gd_jacs) / len(gd_jacs) if gd_jacs else None,
            "no_guard_min_jaccard": min(ng_jacs) if ng_jacs else None,
            "guarded_min_jaccard": min(gd_jacs) if gd_jacs else None,
        },
        "cases": rows,
        "interpretation_ko": {
            "circuit_breaker_saved_quality": "무가드 Jaccard<0.75 구간에서 guarded가 identity로 구제",
            "gatekeeper_bypass": "초단문은 guarded만 압축 생략 — no_guard는 강제 압축",
        },
        "forbidden_claims": ["track_a_promotion", "production_sla"],
        "boundary_ack": "Compare lane only; mainline untouched.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="No-Guard vs guarded proxy compare (B-track).")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--no-guard-profile", default=str(DEFAULT_NO_GUARD_PROFILE))
    ap.add_argument("--guarded-hardening", default=str(DEFAULT_GUARDED_HARDENING))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    no_guard_profile = Path(args.no_guard_profile)
    guarded_hardening = Path(args.guarded_hardening)
    if not no_guard_profile.is_absolute():
        no_guard_profile = ROOT / no_guard_profile
    if not guarded_hardening.is_absolute():
        guarded_hardening = ROOT / guarded_hardening

    if not input_path.is_file():
        raise SystemExit(f"missing input: {input_path}")

    doc = run_compare(
        input_path,
        no_guard_profile=no_guard_profile,
        guarded_hardening=guarded_hardening,
        dry_run=bool(args.dry_run),
        max_cases=max(0, int(args.max_cases)),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    if not args.dry_run:
        agg = doc.get("aggregate") or {}
        print(
            f"cb_saved={agg.get('circuit_breaker_saved_quality_count')} "
            f"bypass={agg.get('gatekeeper_bypass_count')} "
            f"ng_min_jac={agg.get('no_guard_min_jaccard')} "
            f"gd_min_jac={agg.get('guarded_min_jaccard')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
