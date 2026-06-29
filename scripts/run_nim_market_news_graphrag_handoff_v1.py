#!/usr/bin/env python3
"""NIM synthesis for 2026 market/news Logos GraphRAG report — B-track only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
REGISTRY = ROOT / "docs/final/artifacts/nvidia_nim_model_registry_v1.json"
DEFAULT_MD = ROOT / "reports/logos_2026_market_news_prophecy_graphrag_v1_latest.md"
DEFAULT_INDEX = ROOT / "experiments/nextgen_clean_slate_cpu_v1/SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
DEFAULT_OUT_JSON = ROOT / "reports/nim_market_news_graphrag_handoff_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/nim_market_news_graphrag_handoff_v1_latest.md"


def main() -> int:
    try:
        from dotenv import load_dotenv

        if ENV_PATH.is_file():
            load_dotenv(ENV_PATH, override=False)
    except ImportError:
        pass

    sys.path.insert(0, str(ROOT))
    from scripts.nvidia_nim_common_v1 import api_key, chat_with_fallback

    ap = argparse.ArgumentParser()
    ap.add_argument("--graphrag-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--max-tokens", type=int, default=1000)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    key = api_key()
    if not key:
        print("missing NVIDIA_API_KEY", file=sys.stderr)
        return 2

    graphrag = ""
    if args.graphrag_md.is_file():
        graphrag = args.graphrag_md.read_text(encoding="utf-8", errors="replace")[:7000]
    index_snip = ""
    if args.index_json.is_file():
        idx = json.loads(args.index_json.read_text(encoding="utf-8-sig"))
        index_snip = json.dumps(
            {
                "schema": idx.get("schema"),
                "hypo_label": idx.get("hypo_label"),
                "node_count": len(idx.get("nodes") or []),
                "top_nodes": (idx.get("nodes") or [])[:5],
            },
            ensure_ascii=False,
        )[:2500]

    prompt = f"""한국어 [HYPO] B-track. Logos(성경) 렌즈는 [NON_GATING]만.

금지 문구: "성경이 코스피/반도체/지방선거를 예언했다", 매매 GO, Track A 승격.

입력 A — GraphRAG 리포트 발췌:
{graphrag or '(없음)'}

입력 B — archetype index stub:
{index_snip or '(없음)'}

출력만 (다른 서술 금지):
## Field → Lens → Conflict → Final
- Field: (lehman resonance 보조 한 줄)
- Lens 성경 [NON_GATING]: (3불릿)
- Conflict: (1줄)
- Final Action: WATCH 또는 HOLD

## 2026 뉴스 매핑 (표 5행)
| 이벤트 | lane | 절 앵커 |

## operator_next
1. …
2. …
3. …

## 격벽
(한 줄)
끝."""

    registry = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    chat, attempts = chat_with_fallback(key, registry, prompt, args.max_tokens)
    finished = datetime.now(timezone.utc).isoformat()
    model = attempts[-1]["model"] if attempts else ""
    if chat.get("ok"):
        model = chat.get("model", model)

    doc = {
        "schema": "nim_market_news_graphrag_handoff_v1",
        "finished_at_utc": finished,
        "lane": "b_track_research_only",
        "gating": "NON_GATING",
        "model_selected": model,
        "model_attempts": attempts,
        "inputs": {
            "graphrag_md": str(args.graphrag_md),
            "index_json": str(args.index_json),
        },
        "chat": chat,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    body = chat.get("text") or json.dumps(chat, ensure_ascii=False, indent=2)
    args.out_md.write_text(
        f"# NIM · 2026 시장·뉴스 GraphRAG handoff v1\n\n"
        f"**{finished}** · `{model}` · `[HYPO]` `[NON_GATING]`\n\n{body}\n",
        encoding="utf-8",
    )
    if chat.get("ok"):
        print(chat["text"])
        print(f"\n[ok] {args.out_json}\n[ok] {args.out_md}")
        return 0
    print(json.dumps(doc, indent=2, ensure_ascii=False), file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
