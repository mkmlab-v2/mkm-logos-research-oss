#!/usr/bin/env python3
"""Phase 11-T: live golden16 + combined32 cost deep bench + GATE_SPEC refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11t_cost_deep_bench_chain_v1_latest.json"
GOLDEN_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_v1.json"
COMBINED_FIXTURES = ROOT / "tests/fixtures/ollama_shallow_router_golden_combined_stress_v1.json"
GOLDEN_BENCH = ROOT / "reports/ollama_shallow_router_bench_golden16_v1_latest.json"
GOLDEN_GAP = ROOT / "reports/ollama_shallow_routing_oracle_gap_golden16_v1_latest.json"
STRESS_BENCH = ROOT / "reports/ollama_shallow_router_bench_stress_v1_latest.json"
STRESS_GAP = ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
DEEP_BENCH = ROOT / "reports/ollama_shallow_cost_deep_bench_v1_latest.json"


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
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(
        _run("build_combined_fixtures", [PY, "scripts/build_ollama_shallow_router_combined_stress_fixtures_v1.py"])
    )

    bench_common = ["--skip-oracle-gap"]
    if args.skip_ollama:
        bench_common.append("--skip-ollama")

    steps.append(
        _run(
            "bench_golden16",
            [
                PY,
                "scripts/run_ollama_shallow_router_bench_v1.py",
                "--fixtures",
                str(GOLDEN_FIXTURES),
                "--out-json",
                str(GOLDEN_BENCH),
                *bench_common,
            ],
            optional=args.skip_ollama,
        )
    )
    gap_cmd = [
        PY,
        "scripts/build_ollama_shallow_routing_oracle_gap_v1.py",
        "--bench-json",
        str(GOLDEN_BENCH),
        "--fixtures",
        str(GOLDEN_FIXTURES),
        "--out-json",
        str(GOLDEN_GAP),
    ]
    if not args.skip_ollama:
        gap_cmd.extend(["--max-oracle-gap", "0.0"])
    steps.append(_run("oracle_gap_golden16", gap_cmd, optional=args.skip_ollama))

    steps.append(
        _run(
            "bench_combined32",
            [
                PY,
                "scripts/run_ollama_shallow_router_bench_v1.py",
                "--fixtures",
                str(COMBINED_FIXTURES),
                "--out-json",
                str(STRESS_BENCH),
                *bench_common,
            ],
            optional=args.skip_ollama,
        )
    )
    stress_gap_cmd = [
        PY,
        "scripts/build_ollama_shallow_routing_oracle_gap_v1.py",
        "--bench-json",
        str(STRESS_BENCH),
        "--fixtures",
        str(COMBINED_FIXTURES),
        "--out-json",
        str(STRESS_GAP),
    ]
    if not args.skip_ollama:
        stress_gap_cmd.extend(["--max-oracle-gap", "0.0"])
    steps.append(_run("oracle_gap_combined32", stress_gap_cmd, optional=args.skip_ollama))

    steps.append(_run("build_cost_deep_bench", [PY, "scripts/build_ollama_shallow_cost_deep_bench_v1.py"]))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))
        steps.append(
            _run(
                "check_gate_spec_enforce",
                [PY, "scripts/check_universal_root_gate_spec_v1.py", "--enforce-promotion-gates"],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(
            _run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"], optional=True)
        )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_gate_spec",
                [PY, "-m", "pytest", "tests/test_check_universal_root_gate_spec_v1.py", "-q", "--tb=short"],
            )
        )

    deep_doc = _read_json(DEEP_BENCH)
    spec = _read_json(ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json")
    gate_eval = _read_json(ROOT / "reports/universal_root_gate_eval_v1_latest.json")
    ev = gate_eval.get("evaluation") or {}

    core_ok = all(s.get("ok") for s in steps)
    all_ok = core_ok and bool(deep_doc.get("deep_bench_ok")) and bool(ev.get("all_enabled_planes_ok"))

    report = {
        "schema": "logos_graphrag_phase11t_cost_deep_bench_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_promotion_forbidden": True,
        "all_ok": all_ok,
        "ollama_mode": "skipped" if args.skip_ollama else "live",
        "cost_deep_bench": {
            "deep_bench_ok": deep_doc.get("deep_bench_ok"),
            "golden16": (deep_doc.get("profiles") or {}).get("golden16"),
            "combined32": (deep_doc.get("profiles") or {}).get("combined32"),
            "delta_combined32_minus_golden16": deep_doc.get("delta_combined32_minus_golden16"),
        },
        "gate_eval_summary": {
            "research_ready_decision": ev.get("research_ready_decision"),
            "all_enabled_planes_ok": ev.get("all_enabled_planes_ok"),
            "planes": [
                {"plane": p.get("plane"), "enabled": p.get("enabled"), "ok": p.get("ok")}
                for p in (ev.get("planes") or [])
            ],
        },
        "gate_spec_phase": (spec.get("baseline_observed") or {}).get("phase"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11t_cost_deep_bench_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "deep_bench_ok": deep_doc.get("deep_bench_ok"),
                "gate_spec_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
