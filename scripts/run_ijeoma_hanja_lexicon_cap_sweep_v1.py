#!/usr/bin/env python3
"""[HYPO] Sweep max_entries on sample cases — token-proxy saving only (B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ijeoma_cjk_compression_hypo_v1 import (  # noqa: E402
    _load_lexicon_maps,
    compress_ijeoma_cjk_substitution,
)

LANE = ROOT / "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_table_v1.json"
PILOT = ROOT / "reports/constitution/btrack_pilot"
OUT = PILOT / "comp_ijeoma_hanja_lexicon_cap_sweep_v1.json"
CAPS = (4000, 8000, 12000, 20000)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--caps", type=str, default=",".join(str(c) for c in CAPS))
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    caps = [int(x.strip()) for x in args.caps.split(",") if x.strip()]
    cases = json.loads(LANE.read_text(encoding="utf-8")).get("compression_cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    profiles: dict[str, dict] = {}
    for cap in caps:
        _load_lexicon_maps.cache_clear()
        tmp = PILOT / f"ijeoma_hanja_lexicon_cap_{cap}_hypo_tmp.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/export_ijeoma_hanja_codebook_lexicon_hypo_v1.py"),
                "--max-entries",
                str(cap),
                "--out-json",
                str(tmp),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not tmp.is_file():
            profiles[str(cap)] = {"error": proc.stderr[-500:] if proc.stderr else "export_failed"}
            continue
        savings: list[float] = []
        repl = 0
        for case in cases:
            raw = str(case.get("raw_text") or "")
            _, meta = compress_ijeoma_cjk_substitution(raw, tmp)
            savings.append(float(meta.get("token_saving_rate_proxy") or 0.0))
            repl += int(meta.get("replacements") or 0)
        doc = json.loads(tmp.read_text(encoding="utf-8"))
        profiles[str(cap)] = {
            "max_entries": cap,
            "entries_exported": len(doc.get("entries") or []),
            "mean_token_saving_rate_proxy": sum(savings) / len(savings) if savings else 0.0,
            "total_replacements": repl,
            "lexicon_path": str(tmp.relative_to(ROOT)).replace("\\", "/"),
        }

    out = {
        "schema": "comp_ijeoma_hanja_lexicon_cap_sweep_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "sample_case_count": len(cases),
        "profiles": profiles,
    }
    out_path = (ROOT / args.out_json).resolve() if not args.out_json.is_absolute() else args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": out_path.name, "profiles": profiles}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
