#!/usr/bin/env python3
"""DECOY-P0 D0: Ensure zone_tarot / zone_mbti stubs exist; emit readiness JSON ([HYPO] B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARDS = (
    ROOT / "codebook/shards/zone_tarot.json",
    ROOT / "codebook/shards/zone_mbti.json",
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/decoy_experience_layer_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description="DECOY-P0 zone stub readiness (no corpus/graph link).")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    shard_rows = []
    all_ok = True
    for path in SHARDS:
        ok = path.is_file()
        linked = False
        if ok:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            linked = bool(doc.get("corpus_graph_wire_linked"))
            if linked:
                all_ok = False
        shard_rows.append(
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "exists": ok,
                "corpus_graph_wire_linked": linked,
            }
        )

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    doc = {
        "schema": "decoy_experience_layer_readiness_v1",
        "mission_id": "DECOY-P0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "gating_status": "NON_GATING",
        "no_trading_trigger": True,
        "external_copy_rule_ko": (
            "대외: '기만/스모크스크린' 금지 → '캐주얼 체험 레이어 + 프리미엄 다중렌즈 리포트(면책)'. "
            "mkmlife §11: 타로/MBTI는 로딩·스킨만; 메인 포지셔닝은 One-Question Premium."
        ),
        "forbidden_framing": [
            "생존율 300%",
            "구글/애플급 무시무지",
            "의도적 경쟁사 기만",
            "LO-CG-01 재실행",
        ],
        "shards": shard_rows,
        "d0_ok": all_ok and all(r["exists"] for r in shard_rows),
        "next_d1": "mkmlife loading UI + DisclaimerPanel (§10) — no LensReportCard in repo yet [VERIFY]",
        "track_wall": {"corpus_merge": False, "wire_merge": False, "track_a_auto": False},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0 if doc["d0_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
