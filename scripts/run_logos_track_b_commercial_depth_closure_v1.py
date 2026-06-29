#!/usr/bin/env python3
"""Commercial-depth closure chain — 12-theme deep push, heatmap, key-verse, MS bundle [HYPO]."""

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
PRESETS = ROOT / "docs/final/artifacts/LOGOS_TRACK_B_THEME_PRESETS_V1.json"
OUT_DEFAULT = ROOT / "reports/logos_track_b_commercial_depth_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_presets() -> list[str]:
    doc = json.loads(PRESETS.read_text(encoding="utf-8-sig"))
    return list((doc.get("themes") or {}).keys())


def _run(name: str, cmd: list[str], *, timeout: int = 3600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-deep-push", action="store_true")
    ap.add_argument("--skip-phase-h", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    theme_ids = _load_presets()
    steps: list[dict[str, Any]] = []

    if not args.skip_deep_push:
        deep_cmd = [PY, "scripts/run_logos_track_b_themed_deep_push_v1.py"]
        for tid in theme_ids:
            deep_cmd.extend(["--theme", tid])
        steps.append(_run("themed_deep_push_all", deep_cmd, timeout=7200))

    if not args.skip_phase_h:
        steps.append(_run("phase_h_wiring", [PY, "scripts/run_logos_track_b_phase_h_v1.py"], timeout=3600))

    steps.append(
        _run(
            "key_verse_shadow_extended",
            [
                PY,
                "scripts/build_logos_key_verses_shadow_v1.py",
                "--top-n",
                "512",
                "--supplement-deep-push",
                "--supplement-anchor",
            ],
        )
    )
    steps.append(
        _run(
            "key_verse_v2",
            [
                PY,
                "scripts/refine_31k_key_verse_shadow_v2.py",
                "--min-confidence",
                "0.55",
                "--min-citation-hits",
                "1",
                "--top-n",
                "256",
            ],
        )
    )
    steps.append(_run("book_heatmap", [PY, "scripts/build_logos_canon_book_coverage_heatmap_v1.py"]))
    steps.append(_run("lexicon_dual_ab", [PY, "scripts/build_logos_lexicon_4d_dual_ab_report_v1.py"]))
    steps.append(_run("multi_theme_digest", [PY, "scripts/build_logos_track_b_multi_theme_commander_digest_v1.py"]))
    steps.append(_run("product_metrics", [PY, "scripts/build_logos_research_product_metrics_v1.py"]))
    steps.append(_run("ms_bundle", [PY, "scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py"]))
    steps.append(_run("closure_gate", [PY, "scripts/build_logos_commercial_depth_closure_gate_v1.py"]))

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_smoke",
                [
                    PY,
                    "-m",
                    "pytest",
                    "tests/test_logos_track_b_themed_deep_push_v1.py",
                    "tests/test_logos_commercial_depth_closure_v1.py",
                    "-q",
                ],
                timeout=600,
            )
        )

    gate_path = ROOT / "docs/final/artifacts/logos_commercial_depth_closure_v1_latest.json"
    gate_doc: dict[str, Any] = {}
    if gate_path.is_file():
        gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps)
    closure_ok = gate_doc.get("closure_ok") is True
    doc = {
        "schema": "logos_track_b_commercial_depth_closure_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "theme_count": len(theme_ids),
        "theme_ids": theme_ids,
        "steps": steps,
        "closure_ok": gate_doc.get("closure_ok"),
        "commercial_depth_tier": gate_doc.get("commercial_depth_tier"),
        "all_steps_ok": all_ok,
        "ok": closure_ok and all_ok,
        "reproduce": "py scripts/run_logos_track_b_commercial_depth_closure_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "closure_ok": doc["closure_ok"],
                "tier": doc["commercial_depth_tier"],
                "themes": len(theme_ids),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
