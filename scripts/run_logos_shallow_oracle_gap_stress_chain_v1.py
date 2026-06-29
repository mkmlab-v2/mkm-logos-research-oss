#!/usr/bin/env python3
"""Phase 10-C shallow oracle gap stress: combined fixtures bench + gap report [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_COMBINED = ROOT / "tests/fixtures/ollama_shallow_router_golden_combined_stress_v1.json"
DEFAULT_BENCH_OUT = ROOT / "reports/ollama_shallow_router_bench_stress_v1_latest.json"
DEFAULT_GAP_OUT = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
DEFAULT_CHAIN_OUT = ROOT / "reports/logos_shallow_oracle_gap_stress_chain_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_COMBINED)
    ap.add_argument("--bench-out", type=Path, default=DEFAULT_BENCH_OUT)
    ap.add_argument("--gap-out", type=Path, default=DEFAULT_GAP_OUT)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument(
        "--max-oracle-gap",
        type=float,
        default=None,
        help="Fail if routing_oracle_gap exceeds threshold (live bench only)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(
        _run("build_combined_fixtures", [PY, "scripts/build_ollama_shallow_router_combined_stress_fixtures_v1.py"])
    )

    bench_cmd = [
        PY,
        "scripts/run_ollama_shallow_router_bench_v1.py",
        "--fixtures",
        str(args.fixtures),
        "--out-json",
        str(args.bench_out),
        "--skip-oracle-gap",
    ]
    if args.skip_ollama:
        bench_cmd.append("--skip-ollama")
    steps.append(_run("shallow_router_bench_stress", bench_cmd, optional=args.skip_ollama))

    if args.skip_ollama:
        stub = {
            "schema": "ollama_shallow_routing_oracle_gap_v1",
            "version": "1.0.0",
            "generated_at_utc": _utc_now(),
            "hypothesis_class": "HYPO",
            "research_only": True,
            "send_gate": "HOLD",
            "mode": "skipped",
            "skip_reason": "skip_ollama",
            "raw": {
                "router_hit_rate": None,
                "routing_oracle_gap": None,
                "cloud_skip_ratio": None,
                "deep_routing_recall": None,
                "rows": 0,
            },
            "delta": {"routing_oracle_gap_delta_repair_v2_minus_raw": 0.0},
            "rows": [],
        }
        args.gap_out.parent.mkdir(parents=True, exist_ok=True)
        args.gap_out.write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        steps.append(
            {
                "label": "oracle_gap_stress",
                "cmd": ["skipped"],
                "exit_code": 0,
                "ok": True,
                "tail": "skip_ollama stub gap report",
            }
        )
    else:
        gap_cmd = [
            PY,
            "scripts/build_ollama_shallow_routing_oracle_gap_v1.py",
            "--bench-json",
            str(args.bench_out),
            "--fixtures",
            str(args.fixtures),
            "--out-json",
            str(args.gap_out),
        ]
        if args.max_oracle_gap is not None:
            gap_cmd.extend(["--max-oracle-gap", str(args.max_oracle_gap)])
        steps.append(_run("oracle_gap_stress", gap_cmd))

    gap_doc = json.loads(args.gap_out.read_text(encoding="utf-8-sig")) if args.gap_out.is_file() else {}
    gap_raw = gap_doc.get("raw") if isinstance(gap_doc.get("raw"), dict) else {}

    all_ok = all(s.get("ok") for s in steps)
    report = {
        "schema": "logos_shallow_oracle_gap_stress_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "fixture_count": len(
            json.loads(args.fixtures.read_text(encoding="utf-8-sig")).get("fixtures", [])
        )
        if args.fixtures.is_file()
        else None,
        "routing_oracle_gap": gap_raw.get("routing_oracle_gap"),
        "router_hit_rate": gap_raw.get("router_hit_rate"),
        "cloud_skip_ratio": gap_raw.get("cloud_skip_ratio"),
        "deep_routing_recall": gap_raw.get("deep_routing_recall"),
        "max_oracle_gap_threshold": args.max_oracle_gap,
        "steps": steps,
        "reproduce": "py scripts/run_logos_shallow_oracle_gap_stress_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "out": str(args.out), "router_hit_rate": gap_raw.get("router_hit_rate")}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
