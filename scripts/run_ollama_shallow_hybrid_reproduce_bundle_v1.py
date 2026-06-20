#!/usr/bin/env python3
"""One-click Hybrid Memory OS reproduce bundle (~10 min) [HYPO].

Offline: pytest + E2E dry-run + domain matrix + oracle gap shadow.
Live (when Ollama reachable): shallow bench 16 fixtures + oracle gap + optional deep live.

Does not push GitHub or open SEND.
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
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/ollama_shallow_hybrid_reproduce_bundle_v1_latest.json"
SHADOW_BENCH = ROOT / "tests/fixtures/ollama_shallow_router_bench_shadow_perfect_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], timeout: int | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-800:]
    return int(proc.returncode), tail


def _ollama_reachable() -> bool:
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--model", default="mkm-shallow-router-v1")
    ap.add_argument("--min-router-hit-rate", type=float, default=0.75)
    ap.add_argument("--max-oracle-gap", type=float, default=0.25)
    ap.add_argument(
        "--include-deep-live",
        action="store_true",
        help="Run logos deep chain live (slow; requires deep chain deps)",
    )
    ap.add_argument("--deep-chain-timeout-sec", type=int, default=360)
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    errors: list[str] = []

    code, tail = _run(
        [
            PY,
            "-m",
            "pytest",
            "tests/test_ollama_shallow_router_bench_v1.py",
            "tests/test_ollama_shallow_routing_oracle_gap_v1.py",
            "tests/test_ollama_shallow_to_semantic_rag_e2e_v1.py",
            "-q",
        ],
        timeout=300,
    )
    steps["pytest_offline"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"pytest_offline exit {code}")

    code, tail = _run(
        [
            PY,
            str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
            "--include-deep-chain-dry-run",
        ],
        timeout=180,
    )
    steps["e2e_dry_run"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"e2e_dry_run exit {code}")

    code, tail = _run(
        [
            PY,
            str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
            "--run-domain-examples",
            str(ROOT / "tests/fixtures/ollama_shallow_e2e_domain_examples_v1.json"),
        ],
        timeout=120,
    )
    steps["domain_matrix"] = {"ok": code == 0, "exit_code": code, "tail": tail}
    if code != 0:
        errors.append(f"domain_matrix exit {code}")

    live = (not args.skip_ollama) and _ollama_reachable()
    steps["ollama_live"] = {"attempted": live, "reachable": live}

    if live:
        bench_out = ROOT / "reports/ollama_shallow_router_bench_v1_latest.json"
        bench_cmd = [
            PY,
            str(ROOT / "scripts/run_ollama_shallow_router_bench_v1.py"),
            "--model",
            args.model,
            "--fail-below-router-hit",
            "--min-router-hit-rate",
            str(args.min_router_hit_rate),
            "--out-json",
            str(bench_out),
        ]
        code, tail = _run(bench_cmd, timeout=600)
        steps["shallow_bench_live"] = {"ok": code == 0, "exit_code": code, "tail": tail}
        if code != 0:
            errors.append(f"shallow_bench_live exit {code}")
        else:
            gap_cmd = [
                PY,
                str(ROOT / "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"),
                "--bench-json",
                str(bench_out),
                "--max-oracle-gap",
                str(args.max_oracle_gap),
            ]
            code, tail = _run(gap_cmd, timeout=60)
            steps["oracle_gap_live"] = {"ok": code == 0, "exit_code": code, "tail": tail}
            if code != 0:
                errors.append(f"oracle_gap_live exit {code}")
    else:
        code, tail = _run(
            [
                PY,
                str(ROOT / "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"),
                "--bench-json",
                str(SHADOW_BENCH),
                "--max-oracle-gap",
                "0.0",
            ],
            timeout=60,
        )
        steps["oracle_gap_shadow"] = {"ok": code == 0, "exit_code": code, "tail": tail}
        if code != 0:
            errors.append(f"oracle_gap_shadow exit {code}")

    if args.include_deep_live:
        code, tail = _run(
            [
                PY,
                str(ROOT / "scripts/run_ollama_shallow_to_semantic_rag_e2e_v1.py"),
                "--include-deep-chain-live",
                "--query",
                "욥이 고난을 받은 이유",
                "--query-id",
                "job_suffering_reason",
                "--deep-chain-timeout-sec",
                str(args.deep_chain_timeout_sec),
            ],
            timeout=args.deep_chain_timeout_sec + 60,
        )
        steps["e2e_deep_live"] = {"ok": code == 0, "exit_code": code, "tail": tail}
        if code != 0:
            errors.append(f"e2e_deep_live exit {code}")

    doc: dict[str, Any] = {
        "schema": "ollama_shallow_hybrid_reproduce_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "steps": steps,
        "ok": not errors,
        "errors": errors,
        "reproduce": "py scripts/run_ollama_shallow_hybrid_reproduce_bundle_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": not errors, "out": str(args.out), "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
