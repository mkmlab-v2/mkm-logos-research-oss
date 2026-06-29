#!/usr/bin/env python3
"""Optional live DART ingest smoke — Samsung primary (back-compat wrapper).

Reproduce:
  py scripts/run_kospi_dart_mda_poc_live_smoke_v1.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_live_runner_v1 import run_corp_live_smoke  # noqa: E402

OUT = ROOT / "reports/kospi_dart_mda_poc_live_smoke_v1_latest.json"
QUERIES = ROOT / "docs/final/fixtures/kospi_dart_mda_live_smoke_queries_v1.json"
CORPUS_LIVE = ROOT / "reports/kospi_dart_mda_corpus_live_v1_latest.json"


def main() -> int:
    doc = run_corp_live_smoke(
        corp_code="00126380",
        corp_name_ko="삼성전자",
        slug="samsung",
        corpus_out=CORPUS_LIVE,
        queries_path=QUERIES,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "skipped": doc.get("skipped"), "artifact": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
