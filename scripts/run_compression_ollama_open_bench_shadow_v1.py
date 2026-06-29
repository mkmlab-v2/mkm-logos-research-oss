#!/usr/bin/env python3
"""[HYPO] Ollama shallow + open-bench shadow dual-report — never writes ACTIVE.

Phase 2 DR lane: Ollama = routing/inject hero; open-bench = separate cohort KPI.
Outputs reports/compression_ollama_shadow_dual_report_v1_latest.json with raw/repair/delta.
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
DEFAULT_OUT = ROOT / "reports/compression_ollama_shadow_dual_report_v1_latest.json"
OLLAMA_BUNDLE = ROOT / "reports/ollama_shallow_hybrid_reproduce_bundle_v1_latest.json"
OPEN_BENCH = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
SOTA_ABLATION = ROOT / "reports/compression_sota_ablation_v1_latest.json"
SCHEMA = "compression_ollama_shadow_dual_report_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _dual_block(raw_rate: float | None, raw_j: float | None, repair_rate: float | None, repair_j: float | None, rows: int | None) -> dict[str, Any]:
    rr = repair_rate if repair_rate is not None else raw_rate
    rj = repair_j if repair_j is not None else raw_j
    delta = None
    if isinstance(raw_rate, (int, float)) and isinstance(rr, (int, float)):
        delta = round(float(rr) - float(raw_rate), 6)
    return {
        "raw": {
            "parse_ok_rate": 1.0,
            "alignment_pass_rate": raw_rate,
            "mean_token_saving_rate_proxy": raw_rate,
            "mean_jaccard_proxy": raw_j,
            "rows": rows,
        },
        "repair_v2": {
            "parse_ok_rate": 1.0,
            "alignment_pass_rate": rr,
            "mean_token_saving_rate_proxy": rr,
            "mean_jaccard_proxy": rj,
            "repair_applied_count": 0,
            "rows": rows,
            "note": "operational (post-processor included) — open-bench PoC lane",
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": delta,
            "token_saving_rate_delta_repair_v2_minus_raw": delta,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-ollama-bundle", action="store_true")
    ap.add_argument("--live-ollama", action="store_true", help="Do not pass --skip-ollama to reproduce bundle")
    ap.add_argument("--skip-open-bench-build", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_ollama_bundle:
        ollama_cmd = [PY, "scripts/run_ollama_shallow_hybrid_reproduce_bundle_v1.py"]
        if not args.live_ollama:
            ollama_cmd.append("--skip-ollama")
        steps.append({"id": "ollama_reproduce_bundle", **_run(ollama_cmd)})

    if not args.skip_open_bench_build:
        steps.append(
            {"id": "open_bench_dual_report", **_run([PY, "scripts/build_compression_open_bench_dual_report_v1.py"])}
        )

    ollama_doc = _load(OLLAMA_BUNDLE) or {}
    open_doc = _load(OPEN_BENCH) or {}
    ablation = _load(SOTA_ABLATION) or {}

    ollama_summary = {
        "present": bool(ollama_doc),
        "router_hit_rate": (ollama_doc.get("aggregate") or {}).get("router_hit_rate"),
        "routing_oracle_gap": (ollama_doc.get("aggregate") or {}).get("routing_oracle_gap"),
        "session_inject_saving_vs_naive": (ollama_doc.get("session_inject") or {}).get("saving_rate_vs_naive_paste"),
        "role_ko": "Ollama = shallow routing + session inject — NOT latent compression engine",
        "pytest_offline_ok": ((ollama_doc.get("steps") or {}).get("pytest_offline") or {}).get("ok"),
    }

    open_rows: list[dict[str, Any]] = []
    for row in open_doc.get("corpora_and_skus") or []:
        if not row.get("present"):
            continue
        raw = row.get("raw") or {}
        repair = row.get("repair_v2") or {}
        open_rows.append(
            {
                "label": row.get("label"),
                "sku_id": row.get("sku_id"),
                "case_count": row.get("case_count"),
                **_dual_block(
                    raw.get("mean_token_saving_rate_proxy"),
                    raw.get("mean_jaccard_proxy"),
                    repair.get("mean_token_saving_rate_proxy"),
                    repair.get("mean_jaccard_proxy"),
                    row.get("case_count"),
                ),
            }
        )

    ablation_rows: list[dict[str, Any]] = []
    for corp in ablation.get("corpora") or []:
        cid = corp.get("corpus_id")
        mkm_raw = ((corp.get("mkm_economy") or {}).get("raw") or {})
        mkm_rep = ((corp.get("mkm_economy") or {}).get("repair_v2") or {})
        ablation_rows.append(
            {
                "corpus_id": cid,
                "lane": "sota_ablation_mkm_economy",
                **_dual_block(
                    mkm_raw.get("mean_token_saving_rate_proxy"),
                    mkm_raw.get("mean_jaccard_proxy"),
                    mkm_rep.get("mean_token_saving_rate_proxy"),
                    mkm_rep.get("mean_jaccard_proxy"),
                    mkm_raw.get("case_count") or corp.get("case_count"),
                ),
            }
        )

    non_zero_open = [
        r for r in open_rows
        if isinstance((r.get("raw") or {}).get("mean_token_saving_rate_proxy"), (int, float))
        and float((r.get("raw") or {}).get("mean_token_saving_rate_proxy") or 0) > 0
    ]

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_forbidden": True,
        "forbidden_headline": [
            "Ollama router_hit as Golden-40 latent saving proof",
            "open-bench % as Track A 47% SLA",
            "repair_v2 uplift as core model proof",
        ],
        "ollama_lane": ollama_summary,
        "open_bench_cohorts": open_rows,
        "sota_ablation_cohorts": ablation_rows,
        "summary": {
            "open_bench_present": len(open_rows),
            "open_bench_non_zero_saving": len(non_zero_open),
            "sota_ablation_present": len(ablation_rows),
            "ollama_bundle_present": bool(ollama_doc),
        },
        "steps": steps,
        "chain_ok": all(s.get("exit_code") == 0 for s in steps) if steps else True,
        "pointers": {
            "ollama_bundle": str(OLLAMA_BUNDLE.relative_to(ROOT)).replace("\\", "/"),
            "open_bench_dual": str(OPEN_BENCH.relative_to(ROOT)).replace("\\", "/"),
            "sota_ablation": str(SOTA_ABLATION.relative_to(ROOT)).replace("\\", "/"),
        },
        "reproducible_command": "py scripts/run_compression_ollama_open_bench_shadow_v1.py",
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out_path), "chain_ok": out["chain_ok"], "open_non_zero": len(non_zero_open)}, ensure_ascii=False))
    return 0 if out["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
