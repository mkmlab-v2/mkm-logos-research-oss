#!/usr/bin/env python3
"""DF-P2-02: Logos corpus regime singularity report ([HYPO] B-track, NON_GATING)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "scripts/core/build_original_corpus_regime_singularity_report_v1.py"
DEFAULT_CANON = ROOT / "data/logos/verse_decoded_v2.jsonl"
DEFAULT_REGIME = ROOT / "data/regimes/regime_map_btc_ext.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_corpus_regime_singularity_report_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _subset_jsonl(src: Path, max_rows: int, dest: Path) -> int:
    n = 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8") as inf, dest.open("w", encoding="utf-8") as out:
        for line in inf:
            if max_rows > 0 and n >= max_rows:
                break
            s = line.strip()
            if not s:
                continue
            out.write(line if line.endswith("\n") else line + "\n")
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="DF-P2-02 logos corpus regime singularity wrapper.")
    ap.add_argument("--canon-jsonl", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--regime-map-json", type=Path, default=DEFAULT_REGIME)
    ap.add_argument("--top-n", type=int, default=50)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = full canon scan")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    canon_path = args.canon_jsonl if args.canon_jsonl.is_absolute() else ROOT / args.canon_jsonl
    if not canon_path.is_file():
        print(f"error: canon jsonl not found: {canon_path}", file=sys.stderr)
        return 2

    regime_path = args.regime_map_json if args.regime_map_json.is_absolute() else ROOT / args.regime_map_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    scan_path = canon_path
    tmp_dir: tempfile.TemporaryDirectory[str] | None = None
    if int(args.max_rows) > 0:
        tmp_dir = tempfile.TemporaryDirectory(prefix="logos_singularity_")
        scan_path = Path(tmp_dir.name) / "canon_subset.jsonl"
        got = _subset_jsonl(canon_path, int(args.max_rows), scan_path)
        if got == 0:
            print("error: canon subset empty", file=sys.stderr)
            return 2

    cmd = [
        sys.executable,
        str(CORE),
        "--canon-only",
        "--canon-jsonl",
        str(scan_path),
        "--regime-map-json",
        str(regime_path),
        "--top-n",
        str(int(args.top_n)),
        "--output-json",
        str(out_path),
    ]
    if args.dry_run:
        print(" ".join(cmd))
        return 0

    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        return int(proc.returncode)

    if not out_path.is_file():
        print(f"error: expected output missing: {out_path}", file=sys.stderr)
        return 2

    doc = json.loads(out_path.read_text(encoding="utf-8-sig"))
    doc["schema"] = "logos_corpus_regime_singularity_report_v1"
    doc["df_mission_id"] = "DF-P2-02"
    doc["wrapped_at_utc"] = _utc_now()
    doc["core_schema"] = "original_corpus_regime_singularity_report_v1"
    doc["track_wall"] = {
        "research_only": True,
        "non_gating": True,
        "hypothesis_tier": "B",
        "no_trade_signals": True,
    }
    doc.setdefault("inputs", {})
    doc["inputs"]["logos_canon_source"] = str(canon_path.resolve()).replace("\\", "/")
    if int(args.max_rows) > 0:
        doc["inputs"]["max_rows_cap"] = int(args.max_rows)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    if tmp_dir is not None:
        tmp_dir.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
