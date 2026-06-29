#!/usr/bin/env python3
"""Merge BTC + KOSPI per-lens hit-rate legs into prophecy_hit_rate_per_lens_latest.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_prophecy_hit_rate_per_lens_v1.py"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_per_lens_latest.json"
KOSPI_SCORE_CANDIDATES = (
    ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_dual_v2_per_date_latest.json",
    ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_30d_dual_parallel_v1.json",
    ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_dual_per_date_latest.json",
    ROOT / "docs/final/artifacts/btrack_prophecy_score_kospi_only_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_builder(
    workspace: Path,
    score_json: Path,
    out_path: Path,
) -> Dict[str, Any]:
    cmd = [
        sys.executable,
        str(BUILDER),
        "--workspace-root",
        str(workspace),
        "--score-json",
        str(score_json),
        "--output",
        str(out_path),
    ]
    proc = subprocess.run(cmd, cwd=str(workspace), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"build_prophecy_hit_rate_per_lens failed ({score_json.name}): {proc.stderr or proc.stdout}"
        )
    raw = json.loads(out_path.read_text(encoding="utf-8-sig"))
    return raw if isinstance(raw, dict) else {}


def _kospi_row_count(score_path: Path) -> int:
    if not score_path.is_file():
        return 0
    try:
        doc = json.loads(score_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return 0
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    return sum(
        1
        for r in rows
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == "kospi"
    )


def _resolve_kospi_score_path(art: Path) -> Path | None:
    for rel in (
        "btrack_prophecy_score_kospi_dual_v2_per_date_latest.json",
        "btrack_prophecy_score_kospi_30d_dual_parallel_v1.json",
        "btrack_prophecy_score_kospi_dual_per_date_latest.json",
        "btrack_prophecy_score_kospi_only_latest.json",
    ):
        candidate = art / rel
        if _kospi_row_count(candidate) > 0:
            return candidate
    return None


def build_per_lens_bundle(workspace: Path | None = None) -> Dict[str, Any]:
    ws = (workspace or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"
    reports = ws / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    btc_tmp = reports / "_per_lens_btc_tmp.json"
    btc_doc = _run_builder(ws, art / "btrack_prophecy_score_latest.json", btc_tmp)

    legs: Dict[str, Any] = dict(btc_doc.get("legs") or {})
    sources = {
        "btc_score": str((art / "btrack_prophecy_score_latest.json").resolve()),
    }
    kospi_score = _resolve_kospi_score_path(art)
    if kospi_score is not None:
        kospi_tmp = reports / "_per_lens_kospi_tmp.json"
        try:
            kospi_doc = _run_builder(ws, kospi_score, kospi_tmp)
            for inst, block in (kospi_doc.get("legs") or {}).items():
                if inst not in legs:
                    legs[inst] = block
                else:
                    existing_ids = {
                        r.get("lens_id")
                        for r in (legs[inst].get("lenses") or [])
                        if isinstance(r, dict)
                    }
                    for row in block.get("lenses") or []:
                        if isinstance(row, dict) and row.get("lens_id") not in existing_ids:
                            legs[inst]["lenses"].append(row)
            sources["kospi_score"] = str(kospi_score.resolve())
            sources["kospi_rows"] = _kospi_row_count(kospi_score)
        except RuntimeError as exc:
            sources["kospi_error"] = str(exc)
    else:
        sources["kospi_skip"] = "no score JSON with instrument==kospi rows"

    merged = {
        "schema": btc_doc.get("schema") or "prophecy_hit_rate_per_lens_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "zeroing_note": btc_doc.get("zeroing_note"),
        "window": btc_doc.get("window"),
        "inputs": btc_doc.get("inputs"),
        "legs": legs,
        "sources": sources,
        "bundle_note": "BTC default score + optional KOSPI-only score merged for maturity D shadow.",
    }
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_per_lens_bundle(args.workspace_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
