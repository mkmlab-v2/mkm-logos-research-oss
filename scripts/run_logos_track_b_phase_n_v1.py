#!/usr/bin/env python3
"""Phase N — Advanced Insight Synthesis (dialectical + cross-theme + multi-insight)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_track_b_phase_n_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 3600) -> dict[str, Any]:
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
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--max-insight-units", type=int, default=8)
    ap.add_argument("--skip-registry", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("cross_theme_bridge", [PY, "scripts/build_logos_cross_theme_invariant_bridge_v1.py"]))
    steps.append(_run("insight_gap_audit", [PY, "scripts/build_logos_insight_gap_audit_v1.py"]))

    dial_cmd = [PY, "scripts/build_logos_dialectical_insight_layers_v1.py"]
    multi_cmd = [PY, "scripts/run_logos_llm_multi_insight_synthesis_v1.py", "--max-units", str(args.max_insight_units)]
    if not args.skip_ollama:
        os.environ["MKM_LOGOS_LLM_DISTILL_ENABLE"] = "1"
        dial_cmd.append("--try-ollama")
    else:
        multi_cmd.append("--skip-ollama")

    steps.append(_run("dialectical_layers", dial_cmd, timeout=3600))
    steps.append(_run("multi_insight_synthesis", multi_cmd, timeout=3600))
    steps.append(_run("b2b_mapping_audit", [PY, "scripts/build_logos_b2b_logic_mapping_audit_v1.py"]))
    steps.append(_run("insight_digest_md", [PY, "scripts/build_logos_insight_synthesis_digest_v1.py"]))

    if not args.skip_registry:
        steps.append(_run("reasoning_registry", [PY, "scripts/build_logos_reasoning_pattern_registry_v1.py"]))

    steps.append(_run("integration_closure", [PY, "scripts/build_logos_track_b_integration_closure_v1.py"]))

    multi = {}
    multi_path = REPORTS / "logos_multi_insight_synthesis_v1_latest.json"
    dial_path = REPORTS / "logos_dialectical_insight_layers_v1_latest.json"
    bridge_path = REPORTS / "logos_cross_theme_invariant_bridge_v1_latest.json"
    if multi_path.is_file():
        multi = json.loads(multi_path.read_text(encoding="utf-8-sig"))
    dial = json.loads(dial_path.read_text(encoding="utf-8-sig")) if dial_path.is_file() else {}
    bridge = json.loads(bridge_path.read_text(encoding="utf-8-sig")) if bridge_path.is_file() else {}

    insight_total = int((multi.get("summary") or {}).get("unit_count") or 0) + int(
        (dial.get("summary") or {}).get("insight_units") or 0
    )
    overall_ok = all(s.get("ok") for s in steps) and insight_total >= 6

    doc = {
        "schema": "logos_track_b_phase_n_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "bible_ai_refs": "docs/final/artifacts/logos_bible_ai_research_refs_v1.json",
        "insight_total_units": insight_total,
        "shared_hubs": (bridge.get("summary") or {}).get("shared_hub_count"),
        "artifacts": {
            "digest_md": "reports/logos_insight_synthesis_digest_v1_latest.md",
            "cross_theme_bridge": "reports/logos_cross_theme_invariant_bridge_v1_latest.json",
            "dialectical_layers": "reports/logos_dialectical_insight_layers_v1_latest.json",
            "multi_insight": "reports/logos_multi_insight_synthesis_v1_latest.json",
            "mapping_audit": "reports/logos_b2b_logic_mapping_audit_v1_latest.json",
        },
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_n_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "insight_total_units": insight_total, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
