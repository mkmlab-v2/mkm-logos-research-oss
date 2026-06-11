#!/usr/bin/env python3
"""Proof Sprint Lv.1–Lv.3 — open corpus + golden40 + handoff bench + evidence pack."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/compression_evidence_lv1_chain_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/compression_open_structured_corpus_manifest_v1_latest.json"
PY = sys.executable
STD_MAX_DEFAULT = 128
LONG_MAX_DEFAULT = 48
GOLDEN40_MAX_DEFAULT = 40


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _line_count(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _run_step(step_id: str, cmd: list[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-handoff", action="store_true")
    ap.add_argument("--skip-open-std", action="store_true")
    ap.add_argument("--skip-open-long", action="store_true")
    ap.add_argument("--skip-golden40", action="store_true")
    ap.add_argument("--skip-expand", action="store_true")
    ap.add_argument("--std-max-cases", type=int, default=STD_MAX_DEFAULT)
    ap.add_argument("--long-max-cases", type=int, default=LONG_MAX_DEFAULT)
    ap.add_argument("--golden40-max-cases", type=int, default=GOLDEN40_MAX_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_expand:
        steps.append(
            _run_step(
                "expand_open_corpus",
                [
                    PY,
                    "scripts/expand_compression_open_structured_corpus_v1.py",
                    "--std-count",
                    str(args.std_max_cases),
                    "--long-count",
                    str(args.long_max_cases),
                ],
            )
        )

    if not args.skip_golden40:
        steps.append(
            _run_step(
                "golden40_public_safe_corpus",
                [
                    PY,
                    "scripts/build_compression_golden40_public_safe_corpus_v1.py",
                    "--max-cases",
                    str(args.golden40_max_cases),
                    "--strict",
                ],
            )
        )

    steps.append(
        _run_step(
            "corpus_manifest",
            [PY, "scripts/build_compression_open_structured_corpus_v1.py", "--strict"],
        )
    )

    std_max = args.std_max_cases
    long_max = args.long_max_cases
    if MANIFEST.is_file():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
            for row in manifest.get("corpora") or []:
                p = row.get("path") or ""
                if p.endswith("stateless_poc_open_structured_v1.jsonl"):
                    std_max = int(row.get("line_count") or std_max)
                elif p.endswith("stateless_poc_open_structured_long_v1.jsonl"):
                    long_max = int(row.get("line_count") or long_max)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    else:
        std_max = _line_count(ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl") or std_max
        long_max = _line_count(ROOT / "data/compression/stateless_poc_open_structured_long_v1.jsonl") or long_max

    if not args.skip_open_std:
        steps.append(
            _run_step(
                "poc_open_structured",
                [
                    PY,
                    "scripts/run_customer_compression_stateless_poc_v1.py",
                    "--input-jsonl",
                    "data/compression/stateless_poc_open_structured_v1.jsonl",
                    "--max-cases",
                    str(std_max),
                    "--out-json",
                    "reports/customer_compression_stateless_poc_open_structured_v1_latest.json",
                ],
            )
        )

    if not args.skip_open_long:
        steps.append(
            _run_step(
                "poc_open_structured_long",
                [
                    PY,
                    "scripts/run_customer_compression_stateless_poc_v1.py",
                    "--input-jsonl",
                    "data/compression/stateless_poc_open_structured_long_v1.jsonl",
                    "--max-cases",
                    str(long_max),
                    "--out-json",
                    "reports/customer_compression_stateless_poc_open_structured_long_v1_latest.json",
                ],
            )
        )

    if not args.skip_golden40:
        steps.append(
            _run_step(
                "poc_golden40_public_safe",
                [
                    PY,
                    "scripts/run_customer_compression_stateless_poc_v1.py",
                    "--input-jsonl",
                    "data/compression/stateless_poc_golden40_public_safe_v1.jsonl",
                    "--max-cases",
                    str(args.golden40_max_cases),
                    "--out-json",
                    "reports/customer_compression_stateless_poc_golden40_public_safe_v1_latest.json",
                    "--relax-pass-gate",
                ],
            )
        )

    if not args.skip_handoff:
        steps.append(
            _run_step("ops_memory_index", [PY, "scripts/build_mkm_ops_memory_index_v1.py"])
        )
        steps.append(
            _run_step(
                "handoff_token_bench",
                [PY, "scripts/bench_mkm_ops_memory_index_token_savings_v1.py"],
            )
        )

    steps.append(
        _run_step(
            "evidence_pack_index",
            [PY, "scripts/build_compression_public_evidence_pack_v0_index_v1.py"],
        )
    )
    steps.append(
        _run_step(
            "reproduce_pack",
            [PY, "scripts/build_compression_public_reproduce_pack_v1.py"],
        )
    )
    steps.append(
        _run_step(
            "media_fact_sheets_sync",
            [PY, "scripts/build_compression_media_fact_sheets_sync_v1.py"],
        )
    )
    steps.append(
        _run_step(
            "a_codeai_reproduce_bundle",
            [PY, "scripts/build_a_codeai_public_reproduce_bundle_v1.py"],
        )
    )
    steps.append(
        _run_step(
            "a_codeai_bench_landing_payload",
            [PY, "scripts/build_a_codeai_public_bench_landing_payload_v1.py"],
        )
    )
    failed = [s for s in steps if s["exit_code"] != 0]
    doc: dict[str, Any] = {
        "schema": "compression_evidence_lv1_chain_v1",
        "generated_at_utc": _utc(),
        "proof_sprint_level": "lv3",
        "chain_ok": len(failed) == 0,
        "steps": steps,
        "reproduce_pack": "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json",
        "a_codeai_bundle": "docs/final/artifacts/a_codeai_public_reproduce_bundle_v1_latest.json",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    closure_step = _run_step(
        "proof_project_closure",
        [PY, "scripts/build_compression_proof_project_closure_v1.py"],
    )
    steps.append(closure_step)
    if closure_step["exit_code"] != 0:
        failed.append(closure_step)
        doc["chain_ok"] = False
        args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"chain_ok": doc["chain_ok"], "failed_steps": [s["id"] for s in failed]},
            ensure_ascii=False,
        )
    )
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
