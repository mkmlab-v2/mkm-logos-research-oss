#!/usr/bin/env python3
"""Phase 11-G: live Ollama shallow stress 32 fixtures + GATE_SPEC route_stress refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11g_shallow_stress_chain_v1_latest.json"
DEFAULT_STRESS_GAP = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
DEFAULT_MAX_ORACLE_GAP = 0.25


def _utc() -> str:
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


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ollama", action="store_true", help="Offline stub only (CI smoke)")
    ap.add_argument("--max-oracle-gap", type=float, default=DEFAULT_MAX_ORACLE_GAP)
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    stress_cmd = [PY, "scripts/run_logos_shallow_oracle_gap_stress_chain_v1.py"]
    if args.skip_ollama:
        stress_cmd.append("--skip-ollama")
    elif args.max_oracle_gap is not None:
        stress_cmd.extend(["--max-oracle-gap", str(args.max_oracle_gap)])
    steps.append(_run("shallow_oracle_gap_stress_32", stress_cmd, optional=args.skip_ollama))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
    if not args.skip_pytest and args.skip_ollama:
        steps.append(
            _run(
                "pytest_shallow_stress_skip_ollama",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_run_logos_shallow_oracle_gap_stress_chain_v1.py",
                    "-q",
                    "--tb=short",
                ],
                optional=True,
            )
        )

    gap_doc = _read_json(DEFAULT_STRESS_GAP)
    chain_stress_doc = _read_json(ROOT / "reports/logos_shallow_oracle_gap_stress_chain_v1_latest.json")
    gap_raw = gap_doc.get("raw") if isinstance(gap_doc.get("raw"), dict) else {}
    bench_doc = _read_json(ROOT / "reports/ollama_shallow_router_bench_stress_v1_latest.json")
    if gap_doc.get("mode") == "skipped" and chain_stress_doc.get("router_hit_rate") is not None:
        gap_raw = {
            "router_hit_rate": chain_stress_doc.get("router_hit_rate"),
            "routing_oracle_gap": chain_stress_doc.get("routing_oracle_gap"),
            "cloud_skip_ratio": chain_stress_doc.get("cloud_skip_ratio"),
            "deep_routing_recall": chain_stress_doc.get("deep_routing_recall"),
        }
    gate_doc = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    gap_val = gap_raw.get("routing_oracle_gap")
    gap_ok = gap_val is None or args.skip_ollama or float(gap_val) <= float(args.max_oracle_gap)

    all_ok = all(s.get("ok") for s in steps) and gap_ok
    report = {
        "schema": "logos_graphrag_phase11g_shallow_stress_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "live_ollama": not args.skip_ollama,
        "fixture_count": 32,
        "bench_mode": bench_doc.get("mode"),
        "model": bench_doc.get("model"),
        "router_hit_rate": gap_raw.get("router_hit_rate"),
        "routing_oracle_gap": gap_val,
        "cloud_skip_ratio": gap_raw.get("cloud_skip_ratio"),
        "deep_routing_recall": gap_raw.get("deep_routing_recall"),
        "max_oracle_gap_threshold": args.max_oracle_gap,
        "stress_gap_ok": gap_ok,
        "gate_schema_ok": gate_doc.get("schema_validation_ok"),
        "all_enabled_planes_ok": (gate_doc.get("evaluation") or {}).get("all_enabled_planes_ok"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11g_shallow_stress_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "live_ollama": not args.skip_ollama,
                "router_hit_rate": gap_raw.get("router_hit_rate"),
                "routing_oracle_gap": gap_val,
                "stress_gap_ok": gap_ok,
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
