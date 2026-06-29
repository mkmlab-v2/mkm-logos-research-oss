#!/usr/bin/env python3
"""Phase K — router graph_paths sync + commander refresh + MS bundle (no Ollama)."""

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
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"
THEMES = ("dan_aramaic", "john_1_logos")
OUT_DEFAULT = REPORTS / "logos_track_b_phase_k_v1_latest.json"


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
    ap.add_argument("--skip-phase-j", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("graph_paths_sync", [PY, "scripts/sync_logos_themed_router_graph_paths_v1.py"]))

    for theme_id in THEMES:
        locked = ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
        out_json = ART / f"logos_track_b_commander_deep_report_{theme_id}_latest.json"
        out_md = REPORTS / f"logos_track_b_commander_deep_report_{theme_id}_latest.md"
        steps.append(
            _run(
                f"commander_report_{theme_id}",
                [
                    PY,
                    "scripts/run_logos_track_b_commander_deep_report_v1.py",
                    "--distill-json",
                    str(locked),
                    "--output",
                    str(out_json),
                    "--no-fusion",
                    "--no-market-sasang",
                ],
            )
        )
        steps.append(
            _run(
                f"commander_md_{theme_id}",
                [
                    PY,
                    "scripts/build_logos_track_b_commander_report_md_v1.py",
                    "--input",
                    str(out_json),
                    "--distill",
                    str(locked),
                    "--output",
                    str(out_md),
                    "--reproduce-cmd",
                    f"py scripts/run_logos_track_b_phase_k_v1.py",
                ],
            )
        )

    steps.append(_run("macula_reingest", [PY, "scripts/ingest_logos_macula_themed_lemma_edges_v1.py"]))
    steps.append(_run("dual_digest", [PY, "scripts/build_logos_commander_dual_theme_digest_v1.py"]))

    if not args.skip_phase_j:
        steps.append(
            _run(
                "phase_j",
                [PY, "scripts/run_logos_track_b_phase_j_v1.py", "--skip-phase-i", "--skip-ms-pack-rebuild"],
            )
        )

    sync_path = REPORTS / "logos_themed_router_graph_paths_sync_v1_latest.json"
    sync_ok = False
    graph_paths_added = 0
    if sync_path.is_file():
        try:
            sync_doc = json.loads(sync_path.read_text(encoding="utf-8-sig"))
            sync_ok = sync_doc.get("ok") is True
            graph_paths_added = sum(int(t.get("router_paths") or 0) for t in sync_doc.get("themes") or [])
        except json.JSONDecodeError:
            pass

    overall_ok = all(s["ok"] for s in steps) and sync_ok
    doc = {
        "schema": "logos_track_b_phase_k_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "ollama_skipped": True,
        "graph_paths_router_sync": {"ok": sync_ok, "router_paths_per_theme": graph_paths_added},
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_k_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
