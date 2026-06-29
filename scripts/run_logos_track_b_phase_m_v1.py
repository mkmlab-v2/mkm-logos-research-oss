#!/usr/bin/env python3
"""Phase M — 6-topic GraphRAG diagnostic + post-L integration closure + MS bundle."""

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
OUT_DEFAULT = REPORTS / "logos_track_b_phase_m_v1_latest.json"


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


def _macula_tsv_dir() -> Path | None:
    raw = (os.getenv("MACULA_TSV_DIR") or os.getenv("MKM_MACULA_TSV_DIR") or "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_dir() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-macula", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            "topic_graphrag_audit",
            [PY, "scripts/audit_logos_topic_graphrag_seed_retrieval_v1.py"],
        )
    )
    steps.append(
        _run(
            "dual_backend_eval",
            [PY, "scripts/build_logos_themed_retrieval_dual_backend_eval_v1.py"],
        )
    )

    steps.append(
        _run(
            "macula_discovery",
            [PY, "scripts/discover_macula_tsv_dir_v1.py"],
        )
    )
    discovery_path = REPORTS / "macula_tsv_dir_discovery_v1_latest.json"
    macula_dir = _macula_tsv_dir()
    if not macula_dir and discovery_path.is_file():
        try:
            disc = json.loads(discovery_path.read_text(encoding="utf-8-sig"))
            best = disc.get("best") or {}
            if best.get("path"):
                macula_dir = Path(str(best["path"]))
        except json.JSONDecodeError:
            pass

    if not args.skip_macula and macula_dir and macula_dir.is_dir():
        steps.append(
            _run(
                "macula_real_tsv_ingest",
                [
                    PY,
                    "scripts/ingest_logos_macula_themed_lemma_edges_v1.py",
                    "--macula-tsv-dir",
                    str(macula_dir),
                ],
            )
        )
    else:
        steps.append(
            {
                "name": "macula_real_tsv_skipped",
                "ok": True,
                "reason": "no MACULA_TSV_DIR" if not macula_dir else "skip_flag",
            }
        )

    steps.append(_run("integration_closure", [PY, "scripts/build_logos_track_b_integration_closure_v1.py"]))
    steps.append(_run("ms_evidence_pack", [PY, "scripts/build_external_validation_ms_evidence_pack_v1.py"]))
    steps.append(_run("ms_b2b_appendix", [PY, "scripts/build_external_validation_ms_b2b_logic_appendix_v1.py"]))
    steps.append(_run("dual_digest", [PY, "scripts/build_logos_commander_dual_theme_digest_v1.py"]))
    steps.append(_run("ms_logos_bundle", [PY, "scripts/bundle_logos_track_b_into_ms_evidence_pack_v1.py"]))

    closure_path = REPORTS / "logos_track_b_integration_closure_v1_latest.json"
    closure: dict[str, Any] = {}
    if closure_path.is_file():
        try:
            closure = json.loads(closure_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    topic_path = REPORTS / "logos_topic_graphrag_seed_retrieval_v1_latest.json"
    topic_sm: dict[str, Any] = {}
    if topic_path.is_file():
        try:
            topic_sm = (json.loads(topic_path.read_text(encoding="utf-8-sig")) or {}).get("summary") or {}
        except json.JSONDecodeError:
            pass

    overall_ok = all(s.get("ok") for s in steps) and closure.get("ok") is True
    doc = {
        "schema": "logos_track_b_phase_m_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "integration_closure": closure.get("gates"),
        "topic_graphrag_diagnostic": topic_sm,
        "macula_tsv_dir": str(macula_dir) if macula_dir else None,
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_phase_m_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
