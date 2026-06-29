#!/usr/bin/env python3
"""Parallel v2: wave2 manifest+overlay+pilot | clinical snippet smoke (MS HOLD)."""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_V2 = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json"
OVERLAY_V2 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"
PILOT_V2_OUT = ROOT / "reports/lexicon_hangul_curated_pilot_v2_latest.json"
SUMMARY = ROOT / "reports/hangul_curated_parallel_ops_v2_latest.json"


def _run_step(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:] if proc.returncode != 0 else "",
    }


def _job_wave2_chain(py: str) -> dict:
    steps = [
        _run_step([py, "scripts/build_hangul_lexicon_curated_lemma_manifest_v2.py"]),
        _run_step(
            [
                py,
                "scripts/build_master_codebook_hangul_curated_overlay_v1.py",
                "--manifest",
                str(MANIFEST_V2),
                "--out",
                str(OVERLAY_V2),
            ]
        ),
        _run_step(
            [
                py,
                "scripts/run_hangul_curated_ingest_pilot_v1.py",
                "--manifest",
                str(MANIFEST_V2),
                "--overlay-path",
                str(OVERLAY_V2),
                "--out-json",
                str(PILOT_V2_OUT),
                "--skip-rebuild-overlay",
            ]
        ),
    ]
    if OVERLAY_V2.is_file():
        steps.append(
            _run_step(
                [
                    py,
                    "scripts/run_hangul_curated_clinical_snippet_lexicon_smoke_v1.py",
                    "--overlay-v2",
                    str(OVERLAY_V2),
                ]
            )
        )
    ok = all(s["exit_code"] == 0 for s in steps)
    pilot_exit = steps[2]["exit_code"] if len(steps) > 2 else 1
    return {"label": "wave2_chain", "steps": steps, "ok": ok, "pilot_exit": pilot_exit}


def _job_clinical_base(py: str) -> dict:
    step = _run_step([py, "scripts/run_hangul_curated_clinical_snippet_lexicon_smoke_v1.py"])
    return {"label": "clinical_snippet_base", "steps": [step], "ok": step["exit_code"] == 0}


def main() -> int:
    py = sys.executable
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [
            pool.submit(_job_wave2_chain, py),
            pool.submit(_job_clinical_base, py),
        ]
        for fut in as_completed(futs):
            results.append(fut.result())

    wave2 = next((r for r in results if r["label"] == "wave2_chain"), {})
    pilot_rc = wave2.get("pilot_exit", 1)
    summary = {
        "schema": "hangul_curated_parallel_ops_v2",
        "results": results,
        "artifacts": {
            "manifest_v2": str(MANIFEST_V2.relative_to(ROOT)).replace("\\", "/"),
            "overlay_v2": str(OVERLAY_V2.relative_to(ROOT)).replace("\\", "/"),
            "pilot_v2": str(PILOT_V2_OUT.relative_to(ROOT)).replace("\\", "/"),
            "clinical_smoke": "reports/hangul_curated_clinical_snippet_lexicon_smoke_v1_latest.json",
        },
        "ms_paste_headline": "HOLD",
        "apply_forbidden": True,
        "pilot_v2_both_pass": pilot_rc == 0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    all_steps_ok = all(r.get("ok") for r in results)
    return 0 if all_steps_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
