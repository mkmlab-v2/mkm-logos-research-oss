#!/usr/bin/env python3
"""Post-apply smoke: regression · clinical eval · snippet · pointer · pytest (41708 stack)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "reports/hangul_curated_v2_post_apply_smoke_v1_latest.json"
OVERLAY_V2 = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay_v2.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict:
    print("+", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {"cmd": cmd, "exit_code": p.returncode, "stdout_tail": (p.stdout or "")[-800:]}


def main() -> int:
    py = sys.executable
    steps = [
        _run([py, "scripts/check_compression_golden_bench_regression_v1.py", "--min-avg-jaccard", "0.868"]),
        _run([py, "scripts/run_hangul_curated_clinical_evaluate_report_smoke_v1.py", "--include-overlay-v2"]),
        _run([
            py,
            "scripts/run_hangul_curated_clinical_snippet_lexicon_smoke_v1.py",
            "--overlay-v2",
            str(OVERLAY_V2),
        ]),
        _run([py, "scripts/build_master_codebook_bench_lexicon_pointer_v1.py"]),
        _run([
            py,
            "-m",
            "pytest",
            "tests/test_hangul_curated_v2_ms_headline_promotion_packet_v1.py",
            "tests/test_hangul_curated_active_promotion_packet_v1.py",
            "tests/test_hangul_curated_track_a_promotion_packet_v1.py",
            "-q",
            "--tb=no",
        ]),
    ]
    ok = all(s["exit_code"] == 0 for s in steps)
    doc = {
        "schema": "hangul_curated_v2_post_apply_smoke_v1",
        "generated_at_utc": _utc(),
        "steps": steps,
        "chain_ok": ok,
        "production_lexicon": "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_rows_latest.json",
        "active_kpi": "48.8% / J ~0.869",
        "ms_lane_headline": "APPLIED_v2_hangul_curated_ms_lane",
        "ms_submission_archive": "47.5% / 0.890 (unchanged)",
    }
    SUMMARY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(SUMMARY), "ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
