#!/usr/bin/env python3
"""Logos Track B Phase C — ST probe, retrieval eval, delegate chain, external P0/P1."""

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
OUT_DEFAULT = ROOT / "reports/logos_track_b_phase_c_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, ok_exit_codes: set[int] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    ok_codes = ok_exit_codes or {0}
    return {
        "name": name,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode in ok_codes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-external", action="store_true")
    ap.add_argument("--skip-delegate", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            "st_readiness_probe",
            [PY, "scripts/probe_logos_sentence_transformers_readiness_v1.py"],
            ok_exit_codes={0, 1},
        )
    )
    steps.append(_run("themed_retrieval_eval", [PY, "scripts/build_logos_themed_retrieval_eval_v1.py"]))

    if not args.skip_delegate:
        steps.append(
            _run(
                "delegate_chain",
                [
                    PY,
                    "scripts/run_logos_track_b_delegate_chain_v1.py",
                    "--try-ollama-distill",
                    "--reuse-ollama-smoke",
                ],
            )
        )

    steps.append(_run("dual_theme_digest", [PY, "scripts/build_logos_commander_dual_theme_digest_v1.py"]))

    if not args.skip_external:
        steps.append(
            _run(
                "external_validation_p0_p1",
                [PY, "scripts/run_external_validation_recommended_sequence_v1.py", "--skip-p2"],
            )
        )

    st_path = ROOT / "reports/logos_sentence_transformers_readiness_v1_latest.json"
    st_status = "unknown"
    if st_path.is_file():
        try:
            st_status = json.loads(st_path.read_text(encoding="utf-8-sig")).get("status") or st_status
        except json.JSONDecodeError:
            pass

    eval_path = ROOT / "reports/logos_themed_retrieval_eval_v1_latest.json"
    eval_themes: list[dict[str, Any]] = []
    if eval_path.is_file():
        try:
            eval_themes = json.loads(eval_path.read_text(encoding="utf-8-sig")).get("themes") or []
        except json.JSONDecodeError:
            pass

    core_ok = all(
        s.get("ok")
        for s in steps
        if s.get("name") in ("themed_retrieval_eval", "dual_theme_digest")
        or (s.get("name") == "delegate_chain" and not args.skip_delegate)
        or (s.get("name") == "external_validation_p0_p1" and not args.skip_external)
    )

    summary = {
        "schema": "logos_track_b_phase_c_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "st_readiness": st_status,
        "retrieval_eval": eval_themes,
        "artifacts": {
            "st_probe": "reports/logos_sentence_transformers_readiness_v1_latest.json",
            "retrieval_eval": "reports/logos_themed_retrieval_eval_v1_latest.json",
            "dual_digest": "reports/logos_track_b_commander_dual_theme_digest_latest.md",
            "delegate_chain": "reports/logos_track_b_delegate_chain_v1_latest.json",
            "external_sequence": "reports/external_validation_recommended_sequence_v1_latest.json",
        },
        "steps": steps,
        "core_ok": core_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_c_v1.py",
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": core_ok, "out": str(out_path.relative_to(ROOT)), "st": st_status}, ensure_ascii=False))
    return 0 if core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
