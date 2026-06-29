#!/usr/bin/env python3
"""Phase H — themed anchor bridges + GraphRAG re-route + xref + seed audit + digest."""

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
PRESETS = ART / "LOGOS_TRACK_B_THEME_PRESETS_V1.json"
THEMED_REGISTRY = ART / "logos_concept_bridge_registry_themed_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/logos_track_b_phase_h_v1_latest.json"


def _theme_ids_from_presets(presets: dict[str, Any]) -> list[str]:
    return list((presets.get("themes") or {}).keys())


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _run(name: str, cmd: list[str], *, timeout: int = 900) -> dict[str, Any]:
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
    ap.add_argument("--max-bridge-paths", type=int, default=24)
    ap.add_argument("--top-bridges", type=int, default=3)
    ap.add_argument("--skip-xref-rebuild", action="store_true")
    args = ap.parse_args()

    presets = _load(PRESETS) or {}
    theme_ids = _theme_ids_from_presets(presets)
    steps: list[dict[str, Any]] = []

    for theme_id in theme_ids:
        steps.append(
            _run(
                f"build_bridge_{theme_id}",
                [
                    PY,
                    "scripts/build_logos_themed_anchor_concept_bridge_v1.py",
                    "--theme",
                    theme_id,
                    "--max-paths",
                    str(args.max_bridge_paths),
                ],
            )
        )

    steps.append(_run("merge_themed_registry", [PY, "scripts/merge_logos_themed_concept_bridge_registry_v1.py"]))

    for theme_id in theme_ids:
        theme = (presets.get("themes") or {}).get(theme_id) or {}
        query = str(theme.get("graphrag_query_ko") or theme_id)
        out_path = ART / f"logos_subgraph_graphrag_router_{theme_id}_latest.json"
        steps.append(
            _run(
                f"graphrag_router_{theme_id}",
                [
                    PY,
                    "scripts/run_logos_subgraph_graphrag_router_v1.py",
                    "--query",
                    query,
                    "--registry-json",
                    str(THEMED_REGISTRY),
                    "--output-json",
                    str(out_path),
                    "--top-bridges",
                    str(args.top_bridges),
                ],
            )
        )

    if not args.skip_xref_rebuild:
        steps.append(
            _run(
                "xref_subgraph",
                [PY, "scripts/build_logos_themed_xref_subgraph_v1.py", "--min-votes", "10"],
                timeout=600,
            )
        )

    steps.append(_run("router_xref_enrich", [PY, "scripts/enrich_logos_subgraph_router_with_xref_v1.py", "--no-run-router"]))
    steps.append(_run("themed_graphrag_seed_audit", [PY, "scripts/audit_logos_themed_graphrag_seed_retrieval_v1.py"]))
    steps.append(_run("multi_theme_digest", [PY, "scripts/build_logos_track_b_multi_theme_commander_digest_v1.py"]))

    audit_path = ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json"
    audit_summary: dict[str, Any] = {}
    if audit_path.is_file():
        audit_summary = (_load(audit_path) or {}).get("summary") or {}

    organic_hits = str(audit_summary.get("seed_hits_organic") or "0/0")
    organic_num = 0
    organic_den = 1
    if "/" in organic_hits:
        a, b = organic_hits.split("/", 1)
        try:
            organic_num, organic_den = int(a), int(b)
        except ValueError:
            pass
    wiring_ok = organic_num >= max(1, organic_den // 4)

    overall_ok = all(s["ok"] for s in steps) and wiring_ok
    doc = {
        "schema": "logos_track_b_phase_h_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "graphrag_seed_audit": audit_summary,
        "wiring_ok": wiring_ok,
        "steps": steps,
        "artifacts": {
            "themed_registry": str(THEMED_REGISTRY.relative_to(ROOT)).replace("\\", "/"),
            "graphrag_audit": "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json",
            "digest": "reports/logos_track_b_multi_theme_commander_digest_latest.md",
        },
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_h_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "seed_hits_organic": organic_hits, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
