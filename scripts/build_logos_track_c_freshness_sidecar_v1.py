#!/usr/bin/env python3
"""Emit Track C freshness sidecar from existing Logos graph bundle (read-only; no LLM).

Reads docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json when present and records
staleness vs bundle ts_utc. Safe for showroom/IP exhibit timing; not an A-track gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"


def _rel_under_root(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_c_freshness_sidecar_v1_latest.json"

SCHEMA = "logos_track_c_freshness_sidecar_v1"
VERSION = "1.0.0"


def _parse_bundle_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE, help="Path to logos_corpus_graph_bundle_v1 JSON")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output sidecar JSON path")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    generated = now.isoformat().replace("+00:00", "Z")

    bundle_present = False
    bundle_ts_utc: str | None = None
    dedupe: str | None = None
    staleness: int | None = None

    if args.bundle.is_file():
        try:
            doc = json.loads(args.bundle.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = None
        else:
            if isinstance(doc, dict) and doc.get("schema") == "logos_corpus_graph_bundle_v1":
                bundle_present = True
                d = doc.get("dedupe_bundle_key_sha256")
                if isinstance(d, str) and len(d) == 64:
                    dedupe = d
                raw_ts = doc.get("ts_utc")
                if isinstance(raw_ts, str):
                    bundle_ts_utc = raw_ts
                bt = _parse_bundle_ts(raw_ts)
                if bt is not None:
                    staleness = max(0, int((now - bt).total_seconds()))

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": generated,
        "hypothesis_tier": "B",
        "track_c_non_gating": True,
        "inputs": {
            "graph_bundle_path": _rel_under_root(args.bundle),
            "graph_bundle_present": bundle_present,
        },
        "freshness": {
            "bundle_ts_utc": bundle_ts_utc,
            "staleness_seconds": staleness,
            "dedupe_bundle_key_sha256_prefix": (dedupe[:16] + "…") if dedupe else None,
        },
        "note": "Exhibit timing metadata only; not a trading or production SLA gate.",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[logos-track-c-freshness] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
