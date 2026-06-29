#!/usr/bin/env python3
"""Sasang rail P3: ablation, literature resolver, interpretive sync, unified stack gate [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/sasang_rail_p3_chain_v1_latest.json"

STEPS: list[tuple[str, str] | tuple[str, str, list[str]]] = [
    (
        "protocol_ablation",
        "run_sasang_4agent_protocol_ablation_v1.py",
        ["--bootstrap-trials", "80", "--ticks", "400"],
    ),
    ("literature_majority_resolve", "resolve_literature_sasang_majority_v1.py"),
    (
        "literature_resolved_validate",
        "validate_sasang_saju_joint_benchmark_jsonl_v1.py",
        ["--path", "data/myeongni/sasang_saju_joint_benchmark_auto_resolved_v1.jsonl"],
    ),
    ("interpretive_bundle", "build_sasang_interpretive_insight_bundle_v1.py"),
    ("rag_excerpt", "build_notebooklm_lens_sasang_rag_excerpt_v1.py"),
    ("nl_packs", "build_notebooklm_lens_source_packs_v1.py"),
    ("p3_gate", "build_sasang_rail_p3_gate_v1.py"),
    ("unified_gate", "build_sasang_rail_unified_gate_v1.py"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    cmd = [PY, str(ROOT / "scripts" / script)] + (extra or [])
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _prior_phases_ok() -> tuple[bool, str]:
    c = ROOT / "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"
    p2 = ROOT / "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"
    for path, key, want in (
        (c, "sasang_rail_status", "containment_ok"),
        (p2, "sasang_rail_p2_status", "enrichment_ok"),
    ):
        if not path.is_file():
            return False, f"missing {path.name}"
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        if not doc.get("gate_ok"):
            return False, f"{path.name} gate_ok false"
        if doc.get(key) != want:
            return False, f"{path.name} {key}!={want}"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--require-prior-phases", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.require_prior_phases:
        ok, detail = _prior_phases_ok()
        steps.append({"name": "prior_phases_check", "ok": ok, "detail": detail})
        if not ok:
            doc = {
                "schema": "sasang_rail_p3_chain_v1",
                "generated_at_utc": _utc(),
                "lane": "track_b_hypo",
                "steps": steps,
                "all_ok": False,
                "reproduce": "py scripts/run_sasang_rail_p3_chain_v1.py --require-prior-phases",
            }
            args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ok": False, "detail": detail}))
            return 1

    for item in STEPS:
        if len(item) == 3:
            name, script, extra = item
            steps.append(_run(name, script, extra))
        else:
            name, script = item  # type: ignore[misc]
            steps.append(_run(name, script))
        if not steps[-1]["ok"]:
            break

    if steps and all(s["ok"] for s in steps) and not args.skip_pytest:
        for test_path in (
            "tests/test_run_sasang_4agent_protocol_ablation_v1.py",
            "tests/test_resolve_literature_sasang_majority_v1.py",
            "tests/test_sasang_rail_p3_v1.py",
        ):
            t0 = time.perf_counter()
            proc = subprocess.run([PY, "-m", "pytest", test_path, "-q"], cwd=ROOT, capture_output=True, text=True)
            steps.append(
                {
                    "name": f"pytest:{test_path}",
                    "exit_code": proc.returncode,
                    "elapsed_sec": round(time.perf_counter() - t0, 2),
                    "stdout_tail": (proc.stdout or "")[-250:],
                    "ok": proc.returncode == 0,
                }
            )
            if proc.returncode != 0:
                break

    p3_path = ROOT / "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"
    unified_path = ROOT / "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
    p3 = json.loads(p3_path.read_text(encoding="utf-8-sig")) if p3_path.is_file() else {}
    unified = json.loads(unified_path.read_text(encoding="utf-8-sig")) if unified_path.is_file() else {}

    doc = {
        "schema": "sasang_rail_p3_chain_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "steps": steps,
        "all_ok": all(s["ok"] for s in steps),
        "p3_gate_ok": p3.get("gate_ok"),
        "sasang_rail_p3_status": p3.get("sasang_rail_p3_status"),
        "unified_gate_ok": unified.get("gate_ok"),
        "sasang_rail_stack_status": unified.get("sasang_rail_stack_status"),
        "send_gate": "HOLD",
        "reproduce": "py scripts/run_sasang_rail_p3_chain_v1.py --require-prior-phases",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["all_ok"],
                "sasang_rail_p3_status": doc.get("sasang_rail_p3_status"),
                "sasang_rail_stack_status": doc.get("sasang_rail_stack_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
