#!/usr/bin/env python3
"""Multi-corp live DART MD&A smoke — Samsung + SK Hynix (observational, non-blocking).

Reproduce:
  py scripts/run_kospi_dart_mda_poc_multi_corp_live_v1.py
"""

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

from scripts.kospi_dart_mda_live_runner_v1 import run_corp_live_smoke  # noqa: E402

CORPS_FIXTURE = ROOT / "docs/final/fixtures/kospi_dart_mda_live_corps_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_dart_mda_poc_multi_corp_live_v1_latest.json"
# Back-compat mirror for single-corp consumers (Samsung primary).
SAMSUNG_SMOKE_LEGACY = ROOT / "reports/kospi_dart_mda_poc_live_smoke_v1_latest.json"
SAMSUNG_CORPUS_LEGACY = ROOT / "reports/kospi_dart_mda_corpus_live_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_multi_corp(*, corps_fixture: Path = CORPS_FIXTURE) -> dict[str, Any]:
    doc = json.loads(corps_fixture.read_text(encoding="utf-8-sig"))
    corps = doc.get("items") or []
    results: list[dict[str, Any]] = []
    all_skipped = True
    all_pass = True

    for corp in corps:
        slug = str(corp.get("slug") or "")
        corp_code = str(corp.get("corp_code") or "")
        corp_name = str(corp.get("corp_name_ko") or "")
        corpus_out = ROOT / str(corp.get("corpus_artifact") or "")
        smoke_out = ROOT / str(corp.get("smoke_artifact") or "")
        queries_path = ROOT / str(corp.get("queries_fixture") or "")

        smoke = run_corp_live_smoke(
            corp_code=corp_code,
            corp_name_ko=corp_name,
            slug=slug,
            corpus_out=corpus_out,
            queries_path=queries_path,
        )
        smoke_out.parent.mkdir(parents=True, exist_ok=True)
        smoke_out.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        gate_path = ROOT / str(corp.get("gate_artifact") or "")
        if smoke.get("skipped"):
            gate_doc = {"ok": True, "skipped": True, "slug": slug, "schema": "kospi_dart_mda_live_gate_v1"}
        elif smoke.get("ok"):
            from scripts.check_kospi_dart_mda_live_gate_v1 import evaluate  # noqa: WPS433

            gate_doc = evaluate(corpus_path=corpus_out, queries_path=queries_path)
            gate_doc["slug"] = slug
        else:
            gate_doc = {"ok": False, "skipped": False, "slug": slug, "schema": "kospi_dart_mda_live_gate_v1"}
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_text(json.dumps(gate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if slug == "samsung" and not smoke.get("skipped"):
            SAMSUNG_SMOKE_LEGACY.write_text(json.dumps(smoke, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if corpus_out.is_file():
                SAMSUNG_CORPUS_LEGACY.write_text(
                    corpus_out.read_text(encoding="utf-8-sig"), encoding="utf-8"
                )

        if not smoke.get("skipped"):
            all_skipped = False
        if not smoke.get("ok") and not smoke.get("skipped"):
            all_pass = False

        results.append(
            {
                "slug": slug,
                "corp_code": corp_code,
                "corp_name_ko": corp_name,
                "ok": smoke.get("ok"),
                "skipped": smoke.get("skipped"),
                "live_gate": smoke.get("live_gate"),
                "corpus_paragraphs": smoke.get("corpus_paragraphs"),
                "smoke_artifact": str(smoke_out.relative_to(ROOT)).replace("\\", "/"),
                "gate_artifact": str(gate_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )

    return {
        "ok": all_pass or all_skipped,
        "skipped": all_skipped,
        "schema": "kospi_dart_mda_poc_multi_corp_live_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "gate_b_status": doc.get("gate_b_status", "deferred"),
        "poc_status": "closed_research_only",
        "corps_fixture": str(corps_fixture.relative_to(ROOT)).replace("\\", "/"),
        "corps": results,
        "multi_corp_pass": all_pass and not all_skipped,
        "reproduce": "py scripts/run_kospi_dart_mda_poc_multi_corp_live_v1.py",
        "note_ko": "Gate B deferred. B2B 덱 KOSPI 카드 금지 유지.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corps-fixture", type=Path, default=CORPS_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = run_multi_corp(corps_fixture=args.corps_fixture)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "docs/final/artifacts/kospi_dart_mda_multi_corp_live_v1_latest.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "skipped": doc.get("skipped"), "artifact": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
