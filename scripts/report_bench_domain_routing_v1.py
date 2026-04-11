#!/usr/bin/env python3
"""Emit DomainSpecificRouter shard assignment for MULTILENS_PERFORMANCE_EVAL_INPUT_V2 compression_cases.

Writes docs/final/artifacts/BENCH_DOMAIN_ROUTING_TABLE_V1.json and prints a TSV-friendly summary.
korean_cohort_proxy: hangul_ratio >= 0.35 (bench-only heuristic, not product routing).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.domain_router import DomainSpecificRouter


def hangul_ratio(s: str) -> float:
    if not s:
        return 0.0
    h = sum(1 for ch in s if "\uac00" <= ch <= "\ud7a3")
    return h / len(s)


def shard_scores(text: str, shards: list[dict]) -> list[tuple[int, str]]:
    words = {w.lower() for w in re.findall(r"[A-Za-z0-9_\uac00-\ud7a3]+", text)}
    out: list[tuple[int, str]] = []
    for shard in shards:
        keys = {str(k).lower() for k in shard.get("routing_keywords", [])}
        score = sum(1 for k in keys if k in words)
        out.append((score, str(shard.get("shard_id", "?"))))
    out.sort(key=lambda x: (-x[0], x[1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Bench domain routing table for compression_cases.")
    ap.add_argument(
        "--input",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "BENCH_DOMAIN_ROUTING_TABLE_V1.json",
    )
    ap.add_argument(
        "--hangul-proxy-threshold",
        type=float,
        default=0.35,
        help="Mark korean_cohort_proxy when hangul_ratio >= this value.",
    )
    args = ap.parse_args()

    inp_path = Path(args.input).resolve()
    if not inp_path.is_file():
        print("FAIL: input not found", inp_path, file=sys.stderr)
        return 1

    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    shards_root = ROOT / "codebook" / "shards"
    shards: list[dict] = []
    for f in sorted(shards_root.glob("zone_*.json")):
        try:
            shards.append(json.loads(f.read_text(encoding="utf-8")))
        except OSError:
            continue

    router = DomainSpecificRouter(shards_root)
    thr = float(args.hangul_proxy_threshold)
    rows: list[dict] = []
    for c in inp["compression_cases"]:
        raw = str(c.get("raw_text", ""))
        r = router.route(raw)
        sc = shard_scores(raw, shards)
        hr = hangul_ratio(raw)
        rows.append(
            {
                "id": str(c.get("id", "")),
                "hangul_ratio": round(hr, 4),
                "korean_cohort_proxy": hr >= thr,
                "winner_shard_id": r.shard_id,
                "zone_c_hit": r.shard_id == "zone_c_hangul",
                "top_keyword_hits": sc[0][0] if sc else 0,
                "top2_shards": sc[:2],
            }
        )

    kc = [x for x in rows if x["korean_cohort_proxy"]]
    zc_ids = [x["id"] for x in rows if x["zone_c_hit"]]
    print("bench_file", inp_path.relative_to(ROOT))
    print("compression_cases", len(rows))
    print(f"korean_cohort_proxy_hangul_ratio>={thr}", len(kc))
    print("routed_zone_c_hangul_count", len(zc_ids), zc_ids)
    print("korean_but_not_zone_c", [x["id"] for x in kc if not x["zone_c_hit"]])
    print("---")
    for x in rows:
        tag = "zone_c" if x["zone_c_hit"] else ("ko" if x["korean_cohort_proxy"] else "en")
        print(
            f"{x['id']}\t{tag}\thr={x['hangul_ratio']:.3f}\tshard={x['winner_shard_id']}\t"
            f"kw_hits={x['top_keyword_hits']}\ttop2={x['top2_shards']}"
        )

    out_json = Path(args.out).resolve()
    payload = {
        "schema": "bench_domain_routing_table_v1",
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "korean_cohort_proxy_rule": f"hangul_ratio >= {thr}",
        "summary": {
            "compression_cases": len(rows),
            "korean_cohort_proxy_count": len(kc),
            "zone_c_hangul_count": len(zc_ids),
            "zone_c_hangul_ids": zc_ids,
            "korean_proxy_not_zone_c_ids": [x["id"] for x in kc if not x["zone_c_hit"]],
        },
        "cases": rows,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: wrote", out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
