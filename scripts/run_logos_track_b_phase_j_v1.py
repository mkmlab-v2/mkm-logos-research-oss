#!/usr/bin/env python3
"""Phase J — MS evidence pack Logos Track B bundle + integration refresh."""

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
OUT_DEFAULT = ROOT / "reports/logos_track_b_phase_j_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 1200) -> dict[str, Any]:
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
    ap.add_argument("--skip-phase-i", action="store_true")
    ap.add_argument("--skip-ms-pack-rebuild", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_phase_i:
        steps.append(_run("phase_i", [PY, "scripts/run_logos_track_b_phase_i_v1.py"], timeout=1200))

    if not args.skip_ms_pack_rebuild:
        steps.append(_run("ms_evidence_pack", [PY, "scripts/build_external_validation_ms_evidence_pack_v1.py"]))

    steps.append(_run("ms_b2b_appendix", [PY, "scripts/build_external_validation_ms_b2b_logic_appendix_v1.py"]))
    steps.append(_run("logos_ms_bundle", [PY, "scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py"]))

    manifest_path = ROOT / "reports/external_validation_ms_evidence_pack_v1_latest/manifest.json"
    bundle_ok = False
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            bundle = manifest.get("track_b_logos_bundle") or {}
            bundle_ok = len(bundle.get("files") or []) >= 4
        except json.JSONDecodeError:
            pass

    overall_ok = all(s["ok"] for s in steps) and bundle_ok
    doc = {
        "schema": "logos_track_b_phase_j_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "ms_pack_bundle_ok": bundle_ok,
        "steps": steps,
        "artifacts": {
            "ms_pack": "reports/external_validation_ms_evidence_pack_v1_latest/",
            "logos_bundle": "reports/external_validation_ms_evidence_pack_v1_latest/logos_track_b/",
            "pointer": "reports/external_validation_ms_evidence_pack_v1_latest/ms_track_b_logos_internal_pointer_v1.txt",
        },
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_j_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "ms_pack_bundle_ok": bundle_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
