#!/usr/bin/env python3
"""Commercial finish chain — MACULA 12-theme, DSS shadow, integration, MS bundle [HYPO]."""

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
OUT_DEFAULT = ROOT / "reports/logos_track_b_commercial_finish_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _theme_csv() -> str:
    doc = json.loads(PRESETS.read_text(encoding="utf-8-sig"))
    return ",".join((doc.get("themes") or {}).keys())


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
    ap.add_argument("--skip-macula", action="store_true")
    ap.add_argument("--skip-dss", action="store_true")
    ap.add_argument("--skip-phase-m", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    themes = _theme_csv()

    if not args.skip_macula:
        steps.append(
            _run(
                "macula_12_theme_ingest",
                [
                    PY,
                    "scripts/ingest_logos_macula_themed_lemma_edges_v1.py",
                    "--themes",
                    themes,
                ],
            )
        )

    if not args.skip_dss:
        steps.append(_run("dss_apocrypha_shadow_lane", [PY, "scripts/run_dss_apocrypha_shadow_lane_v1.py"]))

    if not args.skip_phase_m:
        steps.append(_run("phase_m_integration", [PY, "scripts/run_logos_track_b_phase_m_v1.py", "--skip-macula"]))

    steps.append(_run("integration_closure", [PY, "scripts/build_logos_track_b_integration_closure_v1.py"]))
    steps.append(
        _run(
            "commercial_depth_tail",
            [
                PY,
                "scripts/run_logos_track_b_commercial_depth_closure_v1.py",
                "--skip-deep-push",
                "--skip-phase-h",
            ],
        )
    )
    steps.append(_run("commercial_finish_gate", [PY, "scripts/build_logos_commercial_finish_closure_gate_v1.py"]))
    steps.append(_run("reasoning_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"]))
    steps.append(_run("ms_bundle", [PY, "scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py"]))
    steps.append(
        _run(
            "pytest_smoke",
            [PY, "-m", "pytest", "tests/test_logos_commercial_depth_closure_v1.py", "tests/test_logos_commercial_finish_v1.py", "-q"],
            timeout=300,
        )
    )

    gate_path = ROOT / "docs/final/artifacts/logos_commercial_finish_closure_v1_latest.json"
    gate_doc: dict[str, Any] = {}
    if gate_path.is_file():
        gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps)
    finish_ok = gate_doc.get("finish_ok") is True
    doc = {
        "schema": "logos_track_b_commercial_finish_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "steps": steps,
        "finish_ok": finish_ok,
        "finish_tier": gate_doc.get("finish_tier"),
        "all_steps_ok": all_ok,
        "ok": all_ok and finish_ok,
        "reproduce": "py scripts/run_logos_track_b_commercial_finish_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "finish_ok": finish_ok, "tier": doc["finish_tier"]}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
