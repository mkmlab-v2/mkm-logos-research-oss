#!/usr/bin/env python3
"""High-delegation B-track chain — Sasang 4AI role shadow for 41k lexicon [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/btrack_sasang_41k_hd_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--max-mismatch-rate", type=float, default=0.75)
    args = ap.parse_args()

    repro = "py scripts/run_btrack_sasang_41k_hd_chain_v1.py"
    steps: list[dict[str, Any]] = []
    steps.append(_run("lexicon_shadow", [PY, "scripts/build_btrack_sasang_lexicon_shadow_v1.py"]))
    steps.append(
        _run(
            "role_mismatch_gate",
            [
                PY,
                "scripts/build_btrack_sasang_role_mismatch_gate_v1.py",
                "--max-mismatch-rate",
                str(args.max_mismatch_rate),
            ],
        )
    )
    steps.append(_run("completion_gate", [PY, "scripts/build_btrack_sasang_41k_completion_gate_v1.py"]))
    steps.append(_run("operator_board", [PY, "scripts/build_btrack_sasang_41k_operator_board_v1.py"]))

    shadow_path = ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json"
    completion_path = ROOT / "reports/btrack_sasang_41k_completion_gate_v1_latest.json"
    shadow = json.loads(shadow_path.read_text(encoding="utf-8-sig")) if shadow_path.is_file() else {}
    completion = (
        json.loads(completion_path.read_text(encoding="utf-8-sig")) if completion_path.is_file() else {}
    )

    overall_ok = all(s.get("ok") for s in steps) and completion.get("completion_pass") is True

    doc = {
        "schema": "btrack_sasang_41k_hd_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "delegation_scale": "L",
        "lane": "track_b_hypo",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "content_layer_isolated": True,
        "structure_transplant_only": False,
        "track_a_bridge": False,
        "live_trading_bridge": False,
        "theology_to_sales_forbidden": True,
        "codebook_unmodified": shadow.get("codebook_unmodified"),
        "lexicon_shadow_rows": shadow.get("codebook_entry_count"),
        "mismatch_rate": (shadow.get("mismatch_summary") or {}).get("mismatch_rate"),
        "completion_score": completion.get("completion_score"),
        "completion_pass": completion.get("completion_pass"),
        "ok": overall_ok,
        "steps": steps,
        "reproduce_cmd": repro,
        "operator_board": "reports/btrack_sasang_41k_operator_board_v1_latest.md",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.verbose:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        print(
            json.dumps(
                {
                    "ok": overall_ok,
                    "completion_score": doc["completion_score"],
                    "lexicon_shadow_rows": doc["lexicon_shadow_rows"],
                    "operator_board": doc["operator_board"],
                },
                ensure_ascii=False,
            )
        )
    if overall_ok:
        print(f"\nOpen: {doc['operator_board']}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
