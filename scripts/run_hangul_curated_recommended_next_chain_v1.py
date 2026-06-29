#!/usr/bin/env python3
"""Recommended next: Phase1 clinical evaluate_report || v2 export prep ([HYPO], MS HOLD)."""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports/constitution/btrack_pilot"
OVERLAY_V2 = PILOT / "master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"
CANDIDATE_V2 = PILOT / "master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v2.json"
PILOT_V2_OUT = ROOT / "reports/lexicon_hangul_curated_pilot_v2_latest.json"
SUMMARY = ROOT / "reports/hangul_curated_recommended_next_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": p.returncode,
        "stdout_tail": (p.stdout or "")[-1200:],
        "stderr_tail": (p.stderr or "")[-800:],
    }


def _job_clinical(py: str) -> dict:
    step = _run([py, "scripts/run_hangul_curated_clinical_evaluate_report_smoke_v1.py", "--include-overlay-v2"])
    return {"label": "clinical_evaluate_report", "steps": [step], "ok": step["exit_code"] == 0}


def _job_v2_export_prep(py: str) -> dict:
    steps = []
    steps.append(
        _run(
            [
                py,
                "scripts/build_master_codebook_hangul_curated_export_candidate_v1.py",
                "--overlay",
                str(OVERLAY_V2),
                "--out",
                str(CANDIDATE_V2),
                "--no-require-export-signoff",
            ]
        )
    )
    if steps[-1]["exit_code"] != 0:
        return {"label": "v2_export_prep", "steps": steps, "ok": False}

    steps.append(
        _run(
            [
                py,
                "scripts/run_hangul_curated_ingest_pilot_v1.py",
                "--manifest",
                str((ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v2.json").resolve()),
                "--overlay-path",
                str(CANDIDATE_V2.relative_to(ROOT)).replace("\\", "/"),
                "--out-json",
                str(PILOT_V2_OUT.relative_to(ROOT)).replace("\\", "/"),
                "--skip-rebuild-overlay",
            ]
        )
    )
    pilot_ok = steps[-1]["exit_code"] == 0
    steps.append(_run([py, "scripts/build_hangul_curated_v2_export_prep_packet_v1.py"]))
    packet_rc = steps[-1]["exit_code"]
    return {
        "label": "v2_export_prep",
        "steps": steps,
        "ok": pilot_ok and packet_rc == 0,
        "export_prep_exit": packet_rc,
    }


def main() -> int:
    py = sys.executable
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {
            pool.submit(_job_clinical, py): "clinical",
            pool.submit(_job_v2_export_prep, py): "v2",
        }
        for fut in as_completed(futs):
            results.append(fut.result())

    clinical = next((r for r in results if r["label"] == "clinical_evaluate_report"), {})
    v2prep = next((r for r in results if r["label"] == "v2_export_prep"), {})
    ok = clinical.get("ok") and v2prep.get("ok")

    summary = {
        "schema": "hangul_curated_recommended_next_v1",
        "generated_at_utc": _utc(),
        "hypo_label": "[HYPO]",
        "research_only": True,
        "ms_paste_headline": "HOLD",
        "apply_forbidden": True,
        "results": results,
        "artifacts": {
            "clinical_evaluate_report": "reports/hangul_curated_clinical_evaluate_report_smoke_v1_latest.json",
            "export_candidate_v2": str(CANDIDATE_V2.relative_to(ROOT)).replace("\\", "/"),
            "v2_export_prep_packet": "reports/hangul_curated_v2_export_prep_packet_v1_latest.json",
        },
        "verdict": {
            "chain_ok": ok,
            "production_41687_unchanged": True,
            "next_human_gate": "commander v2 export-merge signoff before H3-style apply",
        },
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(SUMMARY), "ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
