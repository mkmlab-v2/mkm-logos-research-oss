#!/usr/bin/env python3
"""RQ-017: Join compression KPI with L1 bench RTT layers (research_only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_correlation_protocol_v1.json"
KPI = ROOT / "reports" / "constitution" / "btrack_pilot" / "ultra_compression_kpi_summary_latest.json"
BENCH_LOCAL = ROOT / "docs" / "final" / "artifacts" / "bench_l1_api_load_latest.json"
BENCH_VPS = ROOT / "docs" / "final" / "artifacts" / "bench_l1_api_load_summary_vps_latest.json"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_correlation_report_v1_latest.json"
PAYLOAD_SWEEP = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_payload_sweep_v1_latest.json"
VPS_TRIPLET = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_vps_bench_triplet_v1_latest.json"


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _latency_row(bench: dict[str, Any] | None) -> dict[str, Any] | None:
    if not bench:
        return None
    lat = bench.get("latency_ms") if isinstance(bench.get("latency_ms"), dict) else {}
    return {
        "generated_at_utc": bench.get("generated_at_utc"),
        "bench_environment": bench.get("bench_environment"),
        "research_only": bench.get("research_only"),
        "error_rate": bench.get("error_rate"),
        "p50_ms": lat.get("p50"),
        "p95_ms": lat.get("p95"),
        "p99_ms": lat.get("p99"),
        "path": str(bench.get("path")),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--bench-local", type=Path, default=BENCH_LOCAL)
    ap.add_argument("--bench-vps", type=Path, default=BENCH_VPS)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    protocol = _read(PROTOCOL) or {}
    kpi = _read(KPI) or {}
    active = kpi.get("active_kpi") if isinstance(kpi.get("active_kpi"), dict) else {}
    local = _read(args.bench_local)
    vps = _read(args.bench_vps)

    saving = active.get("global_token_saving_rate")
    policy_ok = active.get("ultra_saving_policy_ok")
    jaccard = active.get("avg_reconstruction_fidelity_jaccard")

    local_p95 = (local or {}).get("latency_ms", {}) or {}
    vps_p95 = (vps or {}).get("latency_ms", {}) or {}
    ratio_local_vps = None
    if local_p95.get("p95") and vps_p95.get("p95"):
        try:
            ratio_local_vps = round(float(local_p95["p95"]) / float(vps_p95["p95"]), 3)
        except (TypeError, ZeroDivisionError):
            pass

    findings = []
    if policy_ok:
        findings.append(
            f"Bench compression policy floor {active.get('ultra_saving_policy_min')} met "
            f"(global saving ~{float(saving or 0)*100:.1f}%)."
        )
    else:
        findings.append("Active KPI does not meet ultra_saving_policy_ok — do not cite saving for SLA.")
    findings.append(
        "Loopback p95 is not VPS/edge SLA; use bench_environment=vps_same_host runs for external narrative."
    )
    if ratio_local_vps and ratio_local_vps > 2:
        findings.append(
            f"Local loopback p95 is ~{ratio_local_vps}x VPS snapshot p95 — environment mismatch is material."
        )

    doc = {
        "schema": "compression_board_ms_correlation_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "[HYPO]",
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-017",
        "protocol_ref": str(PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
        "compression_kpi": {
            "source": str(KPI.relative_to(ROOT)).replace("\\", "/"),
            "global_token_saving_rate": saving,
            "ultra_saving_policy_ok": policy_ok,
            "ultra_saving_policy_min": active.get("ultra_saving_policy_min"),
            "avg_reconstruction_fidelity_jaccard": jaccard,
            "ts_utc": kpi.get("ts_utc"),
        },
        "latency_layers": {
            "local_loopback": _latency_row(local),
            "vps_same_host_snapshot": _latency_row(vps),
        },
        "derived": {
            "local_p95_over_vps_p95_ratio": ratio_local_vps,
            "correlation_claim_allowed": False,
            "correlation_claim_note": (
                "Token saving (bench JSONL) and API RTT (HTTP load) are different layers; "
                "no causal join without controlled A/B payload sweep on same host."
            ),
        },
        "findings": findings,
        "next_steps": [
            "Run 3+ VPS benches per compression_board_ms_correlation_protocol_v1.json step 2",
            "Optional payload-size A/B (500/1000/2000 tokens) on same host",
            "Human sign-off before OEM cites any ms figure",
        ],
    }
    triplet = _read(VPS_TRIPLET)
    if triplet:
        derived_triplet = triplet.get("derived") if isinstance(triplet.get("derived"), dict) else {}
        doc["vps_bench_triplet_ref"] = str(VPS_TRIPLET.relative_to(ROOT)).replace("\\", "/")
        doc["vps_bench_triplet"] = {
            "triplet_ok": derived_triplet.get("triplet_ok"),
            "run_count": derived_triplet.get("run_count"),
            "p95_ms_median": derived_triplet.get("p95_ms_median"),
            "p95_ms_min": derived_triplet.get("p95_ms_min"),
            "p95_ms_max": derived_triplet.get("p95_ms_max"),
        }
        if derived_triplet.get("triplet_ok"):
            doc["next_steps"] = [
                s for s in doc["next_steps"] if "3+ VPS benches" not in str(s)
            ] + ["Human sign-off before OEM cites any ms figure"]
            doc["findings"].append(
                f"VPS same-host triplet met ({derived_triplet.get('run_count')} runs); "
                f"p95 median ~{derived_triplet.get('p95_ms_median')} ms "
                f"(range {derived_triplet.get('p95_ms_min')}–{derived_triplet.get('p95_ms_max')})."
            )

    sweep = _read(PAYLOAD_SWEEP)
    if sweep:
        doc["payload_sweep_ref"] = str(PAYLOAD_SWEEP.relative_to(ROOT)).replace("\\", "/")
        doc["payload_sweep"] = {
            "sweep_ok": sweep.get("sweep_ok"),
            "runs": sweep.get("runs"),
            "generated_at_utc": sweep.get("generated_at_utc"),
        }
        if sweep.get("sweep_ok"):
            doc["next_steps"] = [
                s
                for s in doc["next_steps"]
                if "Optional payload-size" not in str(s)
            ] + ["Refresh VPS benches (3+ runs) on same host"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = {
        "out": str(args.out),
        "policy_ok": policy_ok,
        "local_p95_ms": local_p95.get("p95"),
        "vps_p95_ms": vps_p95.get("p95"),
    }
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"WROTE: {args.out}")
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
