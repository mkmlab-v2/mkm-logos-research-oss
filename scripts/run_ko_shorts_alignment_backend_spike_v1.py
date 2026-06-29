#!/usr/bin/env python3
"""Bench faster-whisper vs stable-ts vs whisperx on high-drift ko shorts WAV [HYPO]."""

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

from scripts.ko_shorts_alignment_backend_lib_v1 import (  # noqa: E402
    BACKEND_FASTER_WHISPER,
    BACKEND_STABLE_TS,
    BACKEND_WHISPERX,
    benchmark_alignment_backend_v1,
)
from scripts.ko_shorts_alignment_routing_lib_v1 import (  # noqa: E402
    MODE_AUTO,
    MODE_BENCH_ALL,
    alignment_routing_contract_v1,
    backends_for_bench_all_v1,
    benchmark_routed_backend_v1,
    build_alignment_routing_table_v1,
    load_routing_sidecar_v1,
    normalize_cli_mode_v1,
)

DEFAULT_OUT = ROOT / "reports/ko_shorts_alignment_backend_spike_v1_latest.json"

CASES = [
    {
        "case_id": "web_pansori",
        "wav": "reports/audio/ko_shorts_web_pansori_tedxkr_v1.wav",
        "priority": "high_drift",
    },
    {
        "case_id": "web_deeply",
        "wav": "reports/audio/ko_shorts_web_deeply_read_v1.wav",
        "priority": "low_drift",
    },
    {
        "case_id": "web_youtube_edu",
        "wav": "reports/audio/ko_shorts_web_youtube_edu_v1.wav",
        "priority": "mid_drift",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_spike_report(
    *,
    cases: list[dict[str, Any]],
    backends: tuple[str, ...],
    model_name: str,
) -> dict[str, Any]:
    bench_cases: list[dict[str, Any]] = []
    backend_status: dict[str, str] = {}
    for case in cases:
        wav = ROOT / case["wav"]
        if not wav.is_file():
            bench_cases.append({"case_id": case["case_id"], "ok": False, "error": "wav_missing"})
            continue
        backends_out: dict[str, Any] = {}
        for backend in backends:
            result = benchmark_alignment_backend_v1(
                wav,
                backend,
                model_name=model_name,
                p0_whisper_semantic=(backend == BACKEND_FASTER_WHISPER),
            )
            backends_out[backend] = result
            if result.get("ok"):
                backend_status[backend] = "ok"
            elif backend not in backend_status:
                backend_status[backend] = "unavailable"
        baseline = backends_out.get(BACKEND_FASTER_WHISPER) or {}
        base_drift = float((baseline.get("drift_vs_proportional") or {}).get("start_drift_ms_mean") or 0.0)
        deltas: list[dict[str, Any]] = []
        for backend, res in backends_out.items():
            if backend == BACKEND_FASTER_WHISPER or not res.get("ok"):
                continue
            drift = float((res.get("drift_vs_proportional") or {}).get("start_drift_ms_mean") or 0.0)
            deltas.append(
                {
                    "backend": backend,
                    "start_drift_ms_mean": drift,
                    "delta_minus_faster_whisper_ms": round(drift - base_drift, 2),
                }
            )
        bench_cases.append(
            {
                "case_id": case["case_id"],
                "priority": case.get("priority"),
                "wav": case["wav"],
                "ok": True,
                "backends": backends_out,
                "delta_vs_faster_whisper": deltas,
            }
        )
    return {
        "schema": "ko_shorts_alignment_backend_spike_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "model_name": model_name,
        "backends_tested": list(backends),
        "backend_status": backend_status,
        "drift_note": "start_drift_ms_mean = |P0 semantic/proportional − P1 aligned| gap; not lip-sync pass",
        "cases": bench_cases,
        "reproduce": "powershell -File scripts/Invoke-KoShortsAlignmentSpike_v1.ps1",
    }


def build_routed_spike_report(
    *,
    cases: list[dict[str, Any]],
    mode: str,
    model_name: str,
    routing_sidecar: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    case_ids = [str(c["case_id"]) for c in cases]
    routing_table = build_alignment_routing_table_v1(case_ids, mode=mode, sidecar=routing_sidecar)
    routing_by_id = {r["case_id"]: r for r in routing_table}

    bench_cases: list[dict[str, Any]] = []
    backend_status: dict[str, str] = {}
    for case in cases:
        cid = case["case_id"]
        wav = ROOT / case["wav"]
        route = routing_by_id[cid]
        if not wav.is_file():
            bench_cases.append({"case_id": cid, "ok": False, "error": "wav_missing", "routing": route})
            continue

        routed = benchmark_routed_backend_v1(wav, route["backend"], model_name=model_name)
        result = routed.get("result") or {}
        applied_backend = (
            routed.get("fallback_backend") if routed.get("routing_fallback") else route["backend"]
        )
        if result.get("ok"):
            backend_status[applied_backend] = "ok"
        elif applied_backend not in backend_status:
            backend_status[applied_backend] = "unavailable"

        bench_cases.append(
            {
                "case_id": cid,
                "priority": case.get("priority"),
                "wav": case["wav"],
                "ok": bool(routed.get("ok")),
                "routing": route,
                "alignment_routing_applied": {
                    "selected_backend": route["backend"],
                    "applied_backend": applied_backend,
                    "rule_id": route.get("rule_id"),
                    "reason": route.get("reason"),
                    "routing_fallback": bool(routed.get("routing_fallback")),
                },
                "routed_backend": result,
                "routing_fallback_detail": routed.get("fallback_result") if routed.get("routing_fallback") else None,
            }
        )

    return {
        "schema": "ko_shorts_alignment_backend_spike_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "model_name": model_name,
        "alignment_backend_mode": normalize_cli_mode_v1(mode),
        "alignment_routing": alignment_routing_contract_v1(),
        "alignment_routing_table": routing_table,
        "backends_tested": sorted({r["backend"] for r in routing_table}),
        "backend_status": backend_status,
        "drift_note": "start_drift_ms_mean = |P0 semantic/proportional − P1 aligned| gap; not lip-sync pass",
        "cases": bench_cases,
        "reproduce": "py scripts/run_ko_shorts_alignment_backend_spike_v1.py --alignment-backend auto --cases clinical_sim",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", default="small")
    ap.add_argument("--cases", default="web_pansori", help="case id, clinical_sim, or all")
    ap.add_argument(
        "--alignment-backend",
        default=MODE_AUTO,
        help="auto | faster_whisper | whisperx | stable_ts | bench_all",
    )
    ap.add_argument("--routing-sidecar", type=Path, default=None, help="per-case domain_hint / override JSON")
    ap.add_argument("--domain-hint", default=None, help="apply domain_hint to all selected cases (P1 prep)")
    ap.add_argument("--include-stable-ts", action="store_true", help="bench_all only")
    ap.add_argument("--include-whisperx", action="store_true", help="bench_all only")
    args = ap.parse_args()

    if args.cases == "all":
        selected = CASES
    elif args.cases == "clinical_sim":
        selected = [c for c in CASES if c["case_id"].startswith("web_")]
    else:
        ids = {x.strip() for x in args.cases.split(",") if x.strip()}
        selected = [c for c in CASES if c["case_id"] in ids]

    mode = normalize_cli_mode_v1(args.alignment_backend)
    sidecar_path = args.routing_sidecar if not args.routing_sidecar else (
        (ROOT / args.routing_sidecar) if not args.routing_sidecar.is_absolute() else args.routing_sidecar
    )
    sidecar = load_routing_sidecar_v1(sidecar_path)
    if args.domain_hint:
        for case in selected:
            sidecar.setdefault(case["case_id"], {})["domain_hint"] = args.domain_hint

    if mode == MODE_BENCH_ALL:
        backends = backends_for_bench_all_v1(
            include_stable_ts=args.include_stable_ts,
            include_whisperx=args.include_whisperx,
        )
        report = build_spike_report(cases=selected, backends=backends, model_name=args.model)
        report["alignment_backend_mode"] = MODE_BENCH_ALL
    else:
        report = build_routed_spike_report(
            cases=selected,
            mode=mode,
            model_name=args.model,
            routing_sidecar=sidecar,
        )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(out),
                "backend_status": report.get("backend_status"),
                "case_count": len(report.get("cases") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
