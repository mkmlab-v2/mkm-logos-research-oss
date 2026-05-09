#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "myeongni_stage2_realset_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _collect_candidates(search_dir: Path) -> list[Path]:
    # realset candidate contract: schema == mkm_myeongni_response_v2
    return sorted(search_dir.rglob("*.json"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate check for Stage2 real artifact sample count (myeongni v2).")
    ap.add_argument("--search-dir", type=Path, default=ART)
    ap.add_argument("--min-real-count", type=int, default=50)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when real sample count is below threshold.")
    args = ap.parse_args()

    search_dir = args.search_dir if args.search_dir.is_absolute() else ROOT / args.search_dir
    if not search_dir.exists():
        raise SystemExit(f"search dir not found: {search_dir}")

    found: list[str] = []
    for p in _collect_candidates(search_dir):
        doc = _read_json(p)
        if not doc:
            continue
        if str(doc.get("schema") or "") != "mkm_myeongni_response_v2":
            continue
        found.append(str(p.resolve()))

    real_count = len(found)
    min_count = max(1, int(args.min_real_count))
    pass_gate = real_count >= min_count
    out = {
        "schema": "myeongni_stage2_realset_gate_v1",
        "generated_at_utc": _now(),
        "search_dir": str(search_dir.resolve()),
        "min_real_count": min_count,
        "real_count": real_count,
        "pass": pass_gate,
        "missing_count": 0 if pass_gate else (min_count - real_count),
        "real_sources": found,
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "pass": pass_gate, "real_count": real_count}, ensure_ascii=False))

    if args.strict and not pass_gate:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
