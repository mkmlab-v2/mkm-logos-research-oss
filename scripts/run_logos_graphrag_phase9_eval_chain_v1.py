#!/usr/bin/env python3
"""Phase 9: oracle gap shadow + dual gold eval (subgraph vs Magic Orb) [HYPO, B-track].

Reproducible:
  py scripts/run_logos_graphrag_phase9_eval_chain_v1.py --optional-ollama-bench
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
CHAIN_OUT = ROOT / "reports/logos_graphrag_phase9_eval_chain_v1_latest.json"


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


def _read_summary(path: Path) -> dict:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc.get("summary") if isinstance(doc.get("summary"), dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ollama-bench", action="store_true")
    ap.add_argument("--optional-ollama-bench", action="store_true")
    ap.add_argument("--skip-oracle-gap", action="store_true")
    ap.add_argument("--skip-gold-query-eval", action="store_true")
    ap.add_argument("--skip-subgraph-gold-eval", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    steps: list[dict] = []

    if not args.skip_ollama_bench:
        steps.append(
            _run(
                "ollama_shallow_router_bench",
                [PY, "scripts/run_ollama_shallow_router_bench_v1.py", "--skip-oracle-gap"],
                optional=args.optional_ollama_bench,
            )
        )

    if not args.skip_oracle_gap:
        steps.append(_run("routing_oracle_gap", [PY, "scripts/build_ollama_shallow_routing_oracle_gap_v1.py"]))

    if not args.skip_gold_query_eval:
        steps.append(
            _run(
                "magic_orb_gold_query_eval",
                [PY, "scripts/build_logos_gold_query_eval_report_v1.py"],
                optional=True,
            )
        )

    if not args.skip_subgraph_gold_eval:
        steps.append(
            _run(
                "subgraph_gold_eval_chain",
                [PY, "scripts/run_logos_subgraph_gold_eval_chain_v1.py", "--skip-pytest"],
            )
        )

    if not args.skip_evidence_pack:
        steps.append(_run("evidence_pack_refresh", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"]))

    oracle_doc = {}
    oracle_path = ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_latest.json"
    if oracle_path.is_file():
        oracle_doc = json.loads(oracle_path.read_text(encoding="utf-8-sig"))

    subgraph_summary = _read_summary(ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json")
    magic_orb_summary = _read_summary(ROOT / "reports/logos_gold_query_eval_v1_latest.json")

    all_ok = all(s.get("ok") for s in steps if not s.get("optional"))
    report = {
        "schema": "logos_graphrag_phase9_eval_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "oracle_gap_raw": oracle_doc.get("raw"),
        "dual_gold_eval": {
            "subgraph_gold_required_all_pass": subgraph_summary.get("gold_required_all_pass"),
            "subgraph_hit_at_k_rates": subgraph_summary.get("hit_at_k_rates"),
            "magic_orb_gold_required_all_pass": magic_orb_summary.get("gold_required_all_pass"),
        },
        "steps": steps,
        "reproduce": (
            "py scripts/run_logos_graphrag_phase9_eval_chain_v1.py "
            "--skip-ollama-bench --skip-subgraph-gold-eval"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "subgraph_gold_required_all_pass": subgraph_summary.get("gold_required_all_pass"),
                "magic_orb_gold_required_all_pass": magic_orb_summary.get("gold_required_all_pass"),
                "routing_oracle_gap": (oracle_doc.get("raw") or {}).get("routing_oracle_gap"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
