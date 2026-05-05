# -*- coding: utf-8 -*-
"""Compose Myeongri AI interpretation prompt with recommended external references.

This wrapper combines:
1) deterministic payload prompt assembly (run_myeongri_ai_interpretation_pack_v1.py)
2) normalized external reference recommendation (recommend_myeongri_external_references_v1.py)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Allow direct execution: py scripts/build_myeongri_ai_prompt_with_refs_v1.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.recommend_myeongri_external_references_v1 import (
    DEFAULT_CATALOG,
    build_payload as build_recommendation_payload,
    recommend_entries,
)
from scripts.run_myeongri_ai_interpretation_pack_v1 import build_user_message


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_payload_text(path: Path | None, inline_text: str) -> tuple[str, str]:
    payload = inline_text
    sha = ""
    if path is not None:
        payload = path.read_text(encoding="utf-8")
        payload_obj = json.loads(payload)
        payload = json.dumps(payload_obj, ensure_ascii=False, indent=2)
        sha = _sha256_file(path)
    return payload, sha


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    ap.add_argument("--profile", default="general")
    ap.add_argument("--tag", action="append", default=[], help="Extra recommendation tag")
    ap.add_argument("--query", default="", help="Question/topic hint")
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--deterministic-json", type=Path)
    ap.add_argument("--deterministic-json-inline", default="")
    ap.add_argument("--timeline-md", type=Path)
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument("--sha256", default="", help="Optional override hash")
    ap.add_argument("--artifact-path", action="append", default=[], help="Extra artifact path")
    ap.add_argument(
        "--recommendation-out",
        type=Path,
        help="Optional path to save recommendation payload JSON",
    )
    args = ap.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    recs = recommend_entries(
        catalog=catalog,
        profile=args.profile,
        extra_tags=list(args.tag),
        query=args.query,
        top_n=args.top_n,
    )
    recommendation_payload = build_recommendation_payload(
        catalog_path=args.catalog,
        profile=args.profile,
        extra_tags=list(args.tag),
        query=args.query,
        top_n=args.top_n,
        recommendations=recs,
    )
    if args.recommendation_out:
        args.recommendation_out.write_text(
            json.dumps(recommendation_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    payload_text, auto_sha = _load_payload_text(args.deterministic_json, args.deterministic_json_inline)
    sha = args.sha256.strip() or auto_sha
    timeline = args.timeline_md.read_text(encoding="utf-8") if args.timeline_md else ""

    artifact_paths = list(args.artifact_path)
    artifact_paths.append("docs/final/artifacts/myeongri_external_reference_catalog_latest.json")
    artifact_paths.extend([f"external_ref::{r.get('source_locator', '')}" for r in recs if r.get("source_locator")])

    text = build_user_message(
        sha256_or_empty=sha,
        artifact_paths=artifact_paths,
        deterministic_json_text=payload_text,
        optional_timeline_md=timeline,
        lang=args.lang,
    )
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
