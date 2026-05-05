# -*- coding: utf-8 -*-
"""명리 AI 해석용 유저 메시지 조립(v1): 템플릿 플레이스홀더 치환만 수행(LLM 호출 없음).

SSOT: docs/final/MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md §3
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs" / "final" / "MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_user_message(
    *,
    sha256_or_empty: str,
    artifact_paths: list[str],
    deterministic_json_text: str,
    optional_timeline_md: str,
    lang: str,
) -> str:
    block = """Task: Produce a structured MKM interpretation PROFILE from the following deterministic inputs only.

Context paths (audit):
- fusion_or_complete_json_sha256: {sha}
- artifact_paths: {paths}

Deterministic payload (paste JSON, truncated if needed):
{payload}

Optional macro timeline (Hypothesis only, may be empty):
{timeline}

Required output language: {lang}

Return a single JSON object conforming to schema id myeongri_ai_interpretation_envelope_v1 (see repo docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json).
"""
    paths_fmt = ", ".join(artifact_paths) if artifact_paths else "(none)"
    return block.format(
        sha=sha256_or_empty or "(empty)",
        paths=paths_fmt,
        payload=deterministic_json_text.strip() or "{}",
        timeline=optional_timeline_md.strip() or "(empty)",
        lang=lang,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sha256", default="", help="Deterministic payload digest (hex)")
    ap.add_argument(
        "--artifact-path",
        action="append",
        default=[],
        metavar="REL_PATH",
        help="Repeat for each repo-relative artifact path",
    )
    ap.add_argument(
        "--deterministic-json",
        type=Path,
        help="JSON file to embed (object or array)",
    )
    ap.add_argument(
        "--deterministic-json-inline",
        default="",
        help="Raw JSON string if file omitted",
    )
    ap.add_argument("--timeline-md", type=Path, help="Optional markdown timeline file")
    ap.add_argument("--lang", default="ko", choices=("ko", "en"))
    ap.add_argument(
        "--hash-deterministic-json",
        action="store_true",
        help="Set --sha256 from SHA-256 of --deterministic-json file",
    )
    args = ap.parse_args()

    payload = args.deterministic_json_inline
    if args.deterministic_json is not None:
        payload = args.deterministic_json.read_text(encoding="utf-8")
        obj = json.loads(payload)
        payload = json.dumps(obj, ensure_ascii=False, indent=2)
        if args.hash_deterministic_json:
            args.sha256 = _sha256_file(args.deterministic_json)

    timeline = ""
    if args.timeline_md is not None:
        timeline = args.timeline_md.read_text(encoding="utf-8")

    msg = build_user_message(
        sha256_or_empty=args.sha256,
        artifact_paths=list(args.artifact_path),
        deterministic_json_text=payload,
        optional_timeline_md=timeline,
        lang=args.lang,
    )
    sys.stdout.write(msg)
    if not msg.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
