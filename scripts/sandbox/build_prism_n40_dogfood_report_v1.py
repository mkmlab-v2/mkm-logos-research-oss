#!/usr/bin/env python3
"""[HYPO] Aggregate n40 dogfooding bench outputs into one extension report."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "experiments" / "no_guard_limit_test" / "results"
DEFAULT_OUT = RESULTS / "prism_n40_dogfood_extension_v1_latest.json"

N40_SOURCES = {
    "meta_channel": RESULTS / "prism_meta_channel_bench_n40_v1_latest.json",
    "dynamic_pinset": RESULTS / "prism_dynamic_pinset_bench_n40_v1_latest.json",
    "proxy_meta_wire": RESULTS / "prism_proxy_meta_wire_bench_n40_v1_latest.json",
    "dynamic_heavy": RESULTS / "prism_dynamic_pinset_heavy_bench_n40_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) and not doc.get("dry_run") else None
    except (json.JSONDecodeError, OSError):
        return None


def build_report(*, strict: bool = False) -> dict[str, Any]:
    loaded = {k: _load(p) for k, p in N40_SOURCES.items()}
    missing = [k for k, p in N40_SOURCES.items() if not p.is_file()]
    invalid = [k for k, doc in loaded.items() if doc is None and N40_SOURCES[k].is_file()]

    if strict and (missing or invalid):
        raise SystemExit(f"n40 missing={missing} invalid={invalid}")

    meta = loaded.get("meta_channel") or {}
    dyn = loaded.get("dynamic_pinset") or {}
    wire = loaded.get("proxy_meta_wire") or {}
    heavy = loaded.get("dynamic_heavy") or {}
    m_agg = meta.get("aggregate") or {}
    d_agg = dyn.get("aggregate") or {}
    w_agg = wire.get("aggregate") or {}
    h_agg = heavy.get("aggregate") or {}

    complete = all(loaded.get(k) for k in N40_SOURCES)

    return {
        "schema": "prism_n40_dogfood_extension_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "track_wall": "not_track_a_promotion",
        "corpus": "data/btrack/cursor_coding_compress_bench_v1_n40.jsonl",
        "case_count": 40,
        "complete": complete,
        "summary": {
            "meta_preserves_baseline": f"{m_agg.get('meta_preserves_baseline_count')}/40",
            "meta_avg_jaccard": m_agg.get("meta_channel_avg_jaccard"),
            "prepend_avg_jaccard": m_agg.get("prepend_avg_jaccard"),
            "dynamic_differ_count": d_agg.get("pinset_ids_differ_count"),
            "dynamic_unique_sets": d_agg.get("dynamic_pinset_unique_sets"),
            "dynamic_preserves_baseline": f"{d_agg.get('dynamic_preserves_baseline_count')}/40",
            "wire_poc_pass": w_agg.get("wire_poc_pass"),
            "heavy_differ_count": h_agg.get("pinset_ids_differ_count"),
            "heavy_unique_sets": h_agg.get("dynamic_pinset_unique_sets"),
        },
        "evidence_paths": {k: str(p.relative_to(ROOT)).replace("\\", "/") for k, p in N40_SOURCES.items()},
        "evidence_valid": {k: loaded.get(k) is not None for k in N40_SOURCES},
        "boundary_ack": "n40 extension only; n20 archive trilogy SSOT unchanged.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build n40 dogfood extension report.")
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    doc = build_report(strict=bool(args.strict))
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    print(f"complete={doc.get('complete')}")
    return 0 if doc.get("complete") or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
