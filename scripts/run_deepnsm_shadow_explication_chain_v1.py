#!/usr/bin/env python3
"""Build DeepNSM shadow explication sidecar from NSM crosswalk fixture [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.deepnsm_shadow_explication_lib_v1 import (  # noqa: E402
    DEFAULT_GEMATRIA_LEXICON,
    build_explication_record,
    build_translit_index,
    load_gematria_rows,
)

DEFAULT_FIXTURE = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def build_sidecar(
    samples: list[dict[str, Any]],
    *,
    gematria_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = load_gematria_rows(str(gematria_path.resolve()))
    index = build_translit_index(rows)
    records = [
        build_explication_record(sample, pair_index=i, index=index, rows=rows)
        for i, sample in enumerate(samples)
    ]
    resolved_greek = sum(
        1
        for r in records
        if str((r.get("resolved_probes") or {}).get("greek", {}).get("resolution") or "").startswith(
            "gematria"
        )
    )
    resolved_hebrew = sum(
        1
        for r in records
        if str((r.get("resolved_probes") or {}).get("hebrew", {}).get("resolution") or "").startswith(
            "gematria"
        )
    )
    summary = {
        "pair_count": len(records),
        "gematria_row_count": len(rows),
        "greek_resolved_count": resolved_greek,
        "hebrew_resolved_count": resolved_hebrew,
        "greek_resolved_rate": round(resolved_greek / max(len(records), 1), 4),
        "hebrew_resolved_rate": round(resolved_hebrew / max(len(records), 1), 4),
    }
    return records, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--gematria-lexicon", type=Path, default=DEFAULT_GEMATRIA_LEXICON)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=ROOT / "reports/deepnsm_shadow_explication_chain_v1_latest.json")
    args = ap.parse_args()

    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    gematria = args.gematria_lexicon if args.gematria_lexicon.is_absolute() else ROOT / args.gematria_lexicon
    if not fixture.is_file():
        print(f"ABORT: fixture missing: {fixture}")
        return 1
    if not gematria.is_file():
        print(f"ABORT: gematria lexicon missing: {gematria}")
        return 1

    doc = json.loads(fixture.read_text(encoding="utf-8"))
    samples = doc.get("samples") or []
    if not samples:
        print("ABORT: empty fixture samples")
        return 1

    records, summary = build_sidecar(samples, gematria_path=gematria)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )

    report_doc = {
        "schema": "deepnsm_shadow_explication_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "fixture": _rel(fixture),
        "gematria_lexicon": _rel(gematria),
        "sidecar_out": _rel(args.out),
        "summary": summary,
        "reproduce": (
            f"py scripts/run_deepnsm_shadow_explication_chain_v1.py --fixture {_rel(fixture)}"
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(args.out), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
