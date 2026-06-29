#!/usr/bin/env python3
"""Ingest DART MD&A section (PoC v1/v2) — fixture | manual_paste | dart_zip | dart_api.

TABLE_EXCLUDED_v1: paragraph text only.

Reproduce:
  py scripts/ingest_dart_mda_section_v1.py --mode fixture
  py scripts/ingest_dart_mda_section_v1.py --mode dart_zip --zip-file tests/fixtures/dart_mda_document_v1.zip
  py scripts/ingest_dart_mda_section_v1.py --mode dart_api --rcept-no <14digits>
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_dart_mda_poc_env_v1 import dart_api_key  # noqa: E402
from scripts.kospi_dart_mda_poc_lib_v1 import (  # noqa: E402
    chunk_mda_text_to_paragraphs,
    extract_mda_section,
)
from scripts.parse_dart_document_zip_v1 import extract_text_from_zip_bytes  # noqa: E402

DEFAULT_FIXTURE_PASTE = ROOT / "data/kospi/dart_mda_poc/fixture_mda_paste_v1.txt"
DEFAULT_OUT = ROOT / "docs/final/artifacts/kospi_dart_mda_corpus_v1_latest.json"
DART_DOCUMENT_URL = "https://opendart.fss.or.kr/api/document.xml"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_corpus_doc(
    *,
    paragraphs: list[dict[str, Any]],
    ingest_mode: str,
    corp_name_ko: str,
    corp_code: str | None,
    rcept_no: str | None,
    canon_status: str,
    ingest_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not paragraphs:
        raise ValueError("no_paragraphs_after_ingest")
    doc: dict[str, Any] = {
        "schema": "kospi_dart_mda_corpus_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tier": "B",
        "wires_to_scoring_core": False,
        "canon_status": canon_status,
        "ingest_mode": ingest_mode,
        "corp_name_ko": corp_name_ko,
        "corp_code": corp_code,
        "rcept_no": rcept_no,
        "report_type": "사업보고서",
        "section": "MD&A",
        "section_label_ko": "이사의 경영진단 및 분석의견",
        "table_excluded_v1": True,
        "paragraphs": paragraphs,
        "reproduce": "py scripts/ingest_dart_mda_section_v1.py --mode fixture",
    }
    if ingest_meta:
        doc["ingest_meta"] = ingest_meta
    return doc


def _paragraphs_from_mda_text(mda_text: str) -> list[dict[str, Any]]:
    section = extract_mda_section(mda_text)
    paragraphs = chunk_mda_text_to_paragraphs(section)
    if not paragraphs:
        raise ValueError("no_paragraphs_after_mda_extract")
    return paragraphs


def ingest_fixture() -> dict[str, Any]:
    raw = DEFAULT_FIXTURE_PASTE.read_text(encoding="utf-8")
    paragraphs = _paragraphs_from_mda_text(raw)
    return build_corpus_doc(
        paragraphs=paragraphs,
        ingest_mode="fixture",
        corp_name_ko="삼성전자(픽스처 발췌·합성)",
        corp_code="FIXTURE-00126380",
        rcept_no="FIXTURE-2025-MDNA-0001",
        canon_status="fixture_only",
    )


def ingest_manual_paste(paste_file: Path, corp_name_ko: str, corp_code: str | None, rcept_no: str | None) -> dict[str, Any]:
    raw = paste_file.read_text(encoding="utf-8-sig")
    paragraphs = _paragraphs_from_mda_text(raw)
    return build_corpus_doc(
        paragraphs=paragraphs,
        ingest_mode="manual_paste",
        corp_name_ko=corp_name_ko,
        corp_code=corp_code,
        rcept_no=rcept_no,
        canon_status="partial_ingest",
    )


def ingest_dart_zip(zip_file: Path, corp_name_ko: str, corp_code: str | None, rcept_no: str | None) -> dict[str, Any]:
    parsed = extract_text_from_zip_bytes(zip_file.read_bytes())
    mda_text = str(parsed.get("mda_text") or "")
    if len(mda_text) < 40:
        raise ValueError("mda_section_too_short_after_zip_parse")
    paragraphs = chunk_mda_text_to_paragraphs(mda_text)
    return build_corpus_doc(
        paragraphs=paragraphs,
        ingest_mode="dart_zip",
        corp_name_ko=corp_name_ko,
        corp_code=corp_code,
        rcept_no=rcept_no,
        canon_status="partial_ingest",
        ingest_meta={
            "zip_members_parsed": parsed.get("zip_members_parsed"),
            "combined_char_count": parsed.get("combined_char_count"),
            "mda_char_count": parsed.get("mda_char_count"),
            "parser_schema": parsed.get("schema"),
        },
    )


def ingest_dart_api(rcept_no: str, api_key: str, corp_name_ko: str, corp_code: str | None) -> dict[str, Any]:
    params = urlencode({"crtfc_key": api_key, "rcept_no": rcept_no})
    url = f"{DART_DOCUMENT_URL}?{params}"
    req = Request(url, headers={"User-Agent": "MKM-KOSPI-DART-MDA-POC/1.0"})
    try:
        with urlopen(req, timeout=60) as resp:
            payload = resp.read()
    except URLError as exc:
        raise RuntimeError(f"dart_api_fetch_failed: {exc}") from exc

    parsed = extract_text_from_zip_bytes(payload)
    mda_text = str(parsed.get("mda_text") or "")
    if len(mda_text) < 40:
        raise ValueError("mda_section_too_short_after_api_zip_parse")
    paragraphs = chunk_mda_text_to_paragraphs(mda_text)
    return build_corpus_doc(
        paragraphs=paragraphs,
        ingest_mode="dart_api",
        corp_name_ko=corp_name_ko,
        corp_code=corp_code,
        rcept_no=rcept_no,
        canon_status="partial_ingest",
        ingest_meta={
            "zip_members_parsed": parsed.get("zip_members_parsed"),
            "mda_char_count": parsed.get("mda_char_count"),
            "parser_schema": parsed.get("schema"),
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["fixture", "manual_paste", "dart_zip", "dart_api"], default="fixture")
    ap.add_argument("--paste-file", type=Path, default=DEFAULT_FIXTURE_PASTE)
    ap.add_argument("--zip-file", type=Path, default=None)
    ap.add_argument("--corp-name-ko", default="삼성전자(픽스처 발췌·합성)")
    ap.add_argument("--corp-code", default=None)
    ap.add_argument("--rcept-no", default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    try:
        if args.mode == "fixture":
            doc = ingest_fixture()
        elif args.mode == "manual_paste":
            doc = ingest_manual_paste(args.paste_file, args.corp_name_ko, args.corp_code, args.rcept_no)
        elif args.mode == "dart_zip":
            if not args.zip_file or not args.zip_file.is_file():
                raise ValueError("missing_zip_file")
            doc = ingest_dart_zip(args.zip_file, args.corp_name_ko, args.corp_code, args.rcept_no)
        else:
            api_key = dart_api_key()
            if not api_key:
                print(json.dumps({"ok": False, "error": "missing_DART_API_KEY"}, ensure_ascii=False))
                return 1
            if not args.rcept_no:
                print(json.dumps({"ok": False, "error": "missing_rcept_no"}, ensure_ascii=False))
                return 1
            doc = ingest_dart_api(args.rcept_no, api_key, args.corp_name_ko, args.corp_code)
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifact": str(args.out), "paragraphs": len(doc["paragraphs"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
