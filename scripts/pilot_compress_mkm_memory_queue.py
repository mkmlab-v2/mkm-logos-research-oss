# -*- coding: utf-8 -*-
"""
Pilot: experimental compression on paths from mkm_memory_priority_queue_latest.json.

- Uses the same experimental compressor as multilens eval (strategy/intensity from
  MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json when present).
- **Default: dry-run** — only metrics; never modifies files under ``memory/``.
- Optional --write-samples-dir writes JSON **copies** with pilot_* fields (still no in-place).

Exit 0 always if the run completes; check report for per-file errors.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import (  # noqa: E402
    _compress_experimental,
    _ensure_sensitive_tokens_preserved,
    _jaccard,
    _reconstruct_experimental_from_raw,
    _tokens,
)

DECISION = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
DEFAULT_QUEUE = ROOT / "reports" / "memory" / "mkm_memory_priority_queue_latest.json"
DEFAULT_OUT = ROOT / "reports" / "memory" / "mkm_memory_pilot_compression_latest.json"
MUST_KEEP = {"사상의학", "체질", "sasang", "myeongni", "myeongri", "bible"}


def _paths_from_inventory_csv(csv_path: Path) -> List[Dict[str, Any]]:
    """Build pseudo queue items with rel_path only (for random sampling beyond priority_list)."""
    out: List[Dict[str, Any]] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rp = (row.get("rel_path") or "").strip()
            if rp:
                out.append({"rel_path": rp})
    return out


def _load_profile() -> Dict[str, Any]:
    if not DECISION.is_file():
        return {"strategy": "B", "intensity": "extreme", "use_hangul_principle": True}
    doc = json.loads(DECISION.read_text(encoding="utf-8"))
    sel = doc.get("selected_candidate") or {}
    return {
        "strategy": str(sel.get("strategy", "B")),
        "intensity": str(sel.get("intensity", "extreme")),
        "use_hangul_principle": bool(sel.get("use_hangul_principle", True)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="Skip this many entries from the priority list (e.g. skip huge P1 heads).",
    )
    ap.add_argument("--limit", type=int, default=200, help="Max files from priority list.")
    ap.add_argument(
        "--strategy",
        choices=("A", "B", "C"),
        default=None,
        help="Override MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json selected_candidate.strategy.",
    )
    ap.add_argument(
        "--intensity",
        choices=("high", "ultra", "extreme"),
        default=None,
        help="Override decision JSON intensity (high|ultra|extreme).",
    )
    ap.add_argument(
        "--hangul",
        choices=("on", "off"),
        default=None,
        help="Override decision JSON use_hangul_principle (on=true, off=false).",
    )
    ap.add_argument(
        "--write-samples-dir",
        type=Path,
        default=None,
        help="If set, write one JSON per file with pilot fields (copies only).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--random-sample",
        type=int,
        default=0,
        help="If >0, shuffle paths and take N (ignores start-index). Uses priority_list; "
        "if N exceeds its length, loads paths from --inventory-csv.",
    )
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for --random-sample.")
    ap.add_argument(
        "--inventory-csv",
        type=Path,
        default=ROOT / "reports" / "memory" / "mkm_memory_inventory_latest.csv",
        help="Full inventory CSV (rel_path column) when --random-sample exceeds queue size.",
    )
    args = ap.parse_args()

    if not args.queue_json.is_file():
        print(f"ERROR: missing {args.queue_json}", file=sys.stderr)
        return 2

    qdoc = json.loads(args.queue_json.read_text(encoding="utf-8"))
    random_sample = max(0, int(args.random_sample))
    pool_source = "priority_queue"
    items: List[Dict[str, Any]] = list(qdoc.get("priority_list") or [])
    if random_sample > 0:
        pool: List[Dict[str, Any]] = list(items)
        if len(pool) < random_sample:
            if args.inventory_csv.is_file():
                pool = _paths_from_inventory_csv(args.inventory_csv)
                pool_source = "inventory_csv"
            else:
                print(
                    f"WARNING: random-sample={random_sample} but queue has {len(items)} "
                    f"and missing {args.inventory_csv}",
                    file=sys.stderr,
                )
        rng = random.Random(int(args.seed))
        rng.shuffle(pool)
        items = pool[:random_sample]
    else:
        start = max(0, int(args.start_index))
        items = items[start : start + max(0, int(args.limit))]

    prof = _load_profile()
    if args.strategy is not None:
        prof["strategy"] = args.strategy
    if args.intensity is not None:
        prof["intensity"] = args.intensity
    if args.hangul == "on":
        prof["use_hangul_principle"] = True
    elif args.hangul == "off":
        prof["use_hangul_principle"] = False
    strategy = prof["strategy"]
    intensity = prof["intensity"]
    use_hangul = prof["use_hangul_principle"]

    rows: List[Dict[str, Any]] = []
    savings: List[float] = []
    jaccs: List[float] = []
    sample_index: List[Dict[str, Any]] = []

    for it in items:
        rel = it.get("rel_path") or ""
        path = Path(rel)
        row: Dict[str, Any] = {"rel_path": rel, "ok": False}
        if not path.is_file():
            row["error"] = "missing_file"
            rows.append(row)
            continue
        try:
            raw_doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            row["error"] = f"read_json:{e}"
            rows.append(row)
            continue
        if not isinstance(raw_doc, dict):
            row["error"] = "not_object"
            rows.append(row)
            continue
        content = raw_doc.get("content")
        if not isinstance(content, str):
            content = ""
        raw_len = len(content)
        raw_tok = _tokens(content)
        if raw_len == 0:
            row["skipped"] = "empty_content"
            row["ok"] = True
            rows.append(row)
            continue

        cand = _compress_experimental(
            content,
            strategy=strategy,
            intensity=intensity,
            must_keep=set(MUST_KEEP),
            use_hangul_principle=use_hangul,
        )
        cand = _ensure_sensitive_tokens_preserved(content, cand, set(MUST_KEEP))
        rec = _reconstruct_experimental_from_raw(
            raw=content,
            compressed_candidate=cand,
            use_hangul_principle=use_hangul,
        )
        comp_len = len(cand)
        j = _jaccard(content, rec)
        saving = 1.0 - (comp_len / raw_len) if raw_len else 0.0
        tok_saving = 1.0 - (_tokens(cand) / raw_tok) if raw_tok else 0.0

        row.update(
            {
                "ok": True,
                "raw_chars": raw_len,
                "compressed_chars": comp_len,
                "char_saving_rate": round(saving, 6),
                "token_saving_rate": round(tok_saving, 6),
                "jaccard_raw_vs_reconstruct": round(j, 6),
            }
        )
        savings.append(saving)
        jaccs.append(j)
        rows.append(row)

        if args.write_samples_dir:
            args.write_samples_dir.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]
            out_name = f"pilot_{h}.json"
            sample = dict(raw_doc)
            sample["pilot_compression"] = {
                "source_rel_path": rel,
                "compressed_text": cand,
                "profile": prof,
                "metrics": {k: row[k] for k in row if k not in ("rel_path", "ok")},
            }
            (args.write_samples_dir / out_name).write_text(
                json.dumps(sample, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            sample_index.append(
                {
                    "rel_path": rel,
                    "sample_file": out_name,
                    "raw_chars": row.get("raw_chars"),
                    "compressed_chars": row.get("compressed_chars"),
                    "jaccard_raw_vs_reconstruct": row.get("jaccard_raw_vs_reconstruct"),
                }
            )

    if args.write_samples_dir and sample_index:
        idx_path = args.write_samples_dir / "index.json"
        idx_path.write_text(
            json.dumps({"schema": "mkm_memory_pilot_samples_index_v1", "samples": sample_index}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    n_ok = sum(1 for r in rows if r.get("ok") and "raw_chars" in r)
    mean_saving = sum(savings) / len(savings) if savings else 0.0
    mean_j = sum(jaccs) / len(jaccs) if jaccs else 0.0
    pct_half = (
        sum(1 for r in rows if r.get("ok") and isinstance(r.get("char_saving_rate"), (int, float)) and r["char_saving_rate"] >= 0.5)
        / n_ok
        if n_ok
        else 0.0
    )

    report = {
        "schema": "mkm_memory_pilot_compression_v1",
        "queue_source": str(args.queue_json.resolve()),
        "start_index": int(args.start_index) if random_sample <= 0 else None,
        "random_sample": random_sample if random_sample > 0 else None,
        "random_seed": int(args.seed) if random_sample > 0 else None,
        "pool_source": pool_source if random_sample > 0 else None,
        "profile": prof,
        "must_keep_terms": sorted(MUST_KEEP),
        "limit": int(args.limit),
        "processed": len(rows),
        "ok_with_metrics": n_ok,
        "mean_char_saving_rate": round(mean_saving, 6),
        "mean_jaccard": round(mean_j, 6),
        "fraction_char_saving_ge_0_5": round(pct_half, 6),
        "write_samples_dir": str(args.write_samples_dir.resolve()) if args.write_samples_dir else None,
        "samples_index_json": str((args.write_samples_dir / "index.json").resolve()) if args.write_samples_dir and sample_index else None,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out.resolve()),
                "ok_with_metrics": n_ok,
                "mean_char_saving_rate": report["mean_char_saving_rate"],
                "mean_jaccard": report["mean_jaccard"],
                "fraction_char_saving_ge_0_5": report["fraction_char_saving_ge_0_5"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
