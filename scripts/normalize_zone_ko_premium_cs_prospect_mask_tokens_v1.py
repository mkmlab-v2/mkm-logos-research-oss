#!/usr/bin/env python3
"""Apply ███ mask tokens to KO CS prospects skipped for missing_mask_token.

research_only · prospect-only edits · no production overwrite without merge gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import (  # noqa: E402
    must_keep_terms_for_snippet,
    normalize_snippet,
    snippet_hash,
)

DEFAULT_PROSPECT = ROOT / "codebook/templates/zone_ko_premium_cs_templates_prospect_v1.jsonl"
SHARD = ROOT / "codebook/shards/zone_ko_premium_cs_v1.json"

MASK_FIX_SNIPPETS: dict[str, str] = {
    "kcs_p006": (
        "오늘 상담 건 정리 부탁합니다. ███ 고객 케이스요. ███ 으로 요약 메일 보내 주세요."
    ),
    "kcs_p019": (
        "환불 처리 관련하여 주문번호 ███ 환불 요청합니다. 이*민 명의 결제입니다. "
        "네, 고객님. 이*민 명의로 결제된 내역 확인 도와드리겠습니다. "
        "010-****-1234 로 연락 주세요. 대기 너무 깁니다."
    ),
    "kcs_p020": ("배송 조회해 보니 송장번호 ███ 건이 아직 안 왔어요. 한*별 담당 맞나요?"),
    "kcs_p021": (
        "강의 수강 취소했는데 환불 기한 지났다고 나옵니다. 시스템 오류 아닌가요? "
        "학습자 ID ███ 확인해 주세요."
    ),
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def apply_mask_fixes(
    rows: list[dict[str, Any]],
    *,
    keywords: list[str],
    only_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    patched: list[str] = []
    out: list[dict[str, Any]] = []
    for row in rows:
        tid = str(row.get("template_id") or "")
        if tid in MASK_FIX_SNIPPETS and (only_ids is None or tid in only_ids):
            snippet = normalize_snippet(MASK_FIX_SNIPPETS[tid])
            if "███" not in snippet:
                raise ValueError(f"mask fix missing ███ for {tid}")
            row = {
                **row,
                "snippet": snippet,
                "must_keep_terms": must_keep_terms_for_snippet(snippet, keywords),
                "snippet_sha256": snippet_hash(snippet),
                "mask_normalized": True,
            }
            patched.append(tid)
        out.append(row)
    return out, patched


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize KO CS prospect ███ mask tokens")
    ap.add_argument("--prospect", type=Path, default=DEFAULT_PROSPECT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.prospect.is_file():
        print(f"MISSING prospect: {args.prospect}", file=sys.stderr)
        return 1
    shard = json.loads(SHARD.read_text(encoding="utf-8-sig"))
    from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import shard_keywords

    keywords = shard_keywords(shard)
    rows, patched = apply_mask_fixes(load_rows(args.prospect), keywords=keywords)
    if not args.dry_run:
        write_rows(args.prospect, rows)
    print(json.dumps({"ok": True, "patched": patched, "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
