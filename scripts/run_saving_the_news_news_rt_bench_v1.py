#!/usr/bin/env python3
"""NEWS-RT cohort bench — offline news_observation JSONL (not live stream)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "saving_the_news_news_rt_bench_result_v1_latest.json"
CONTRACT = ART / "saving_the_news_news_rt_bench_contract_v1_latest.json"
DEFAULT_COHORT = ART / "news_observation_v1_latest.jsonl"
MIN_ROWS_DEFAULT = 120


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _tok(s: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9가-힣]+", s.lower()))


def _jaccard(a: str, b: str) -> float:
    sa, sb = _tok(a), _tok(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _token_count(s: str) -> int:
    t = _tok(s)
    return len(t) if t else max(1, len(s.split()))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compress_state_card_v0(text: str, *, target_char_ratio: float = 0.55) -> str:
    """Deterministic research stub — not Track A multilens engine."""
    words = re.findall(r"[A-Za-z0-9가-힣]+", text)
    seen: set[str] = set()
    kept: list[str] = []
    for w in words:
        wl = w.lower()
        if wl in seen:
            continue
        seen.add(wl)
        kept.append(w)
    compact = " ".join(kept)
    target_len = max(1, int(len(text) * target_char_ratio))
    if len(compact) <= target_len:
        return compact
    return compact[:target_len].strip()


def _load_cohort(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("schema_version") != "news_observation_v1":
            raise ValueError(f"unexpected schema_version in {_display_path(path)}")
        rows.append(row)
    return rows


def run_bench(
    cohort_path: Path,
    *,
    min_rows: int = MIN_ROWS_DEFAULT,
    target_char_ratio: float = 0.55,
) -> dict[str, Any]:
    rows = _load_cohort(cohort_path)
    n = len(rows)
    if n < min_rows:
        return {
            "schema": "saving_the_news_news_rt_bench_result_v1",
            "axis_id": "NEWS-RT",
            "lane": "research_only",
            "generated_at_utc": _utc_now(),
            "cohort_id": cohort_path.stem,
            "cohort_source": _display_path(cohort_path),
            "observation_row_count": n,
            "min_rows_required": min_rows,
            "measurement_status": "NOT_MEASURED",
            "status": "COHORT_TOO_SMALL",
            "ready_for_external_send": False,
            "kpi": {
                "token_saving_ratio": None,
                "jaccard_fidelity_proxy": None,
                "integrity_score": None,
                "latency_p99_ms": None,
                "notes": f"Need >= {min_rows} rows; got {n}.",
            },
            "compression_method": "state_card_unique_token_v0",
            "forbidden_interpretation": _forbidden(),
            "contract_ref": _display_path(CONTRACT) if CONTRACT.is_file() else None,
        }

    savings: list[float] = []
    jaccards: list[float] = []
    integrity_hits = 0
    for row in rows:
        raw = str(row.get("canonical_text", ""))
        expected_hash = str(row.get("text_sha256", ""))
        if expected_hash and _sha256_text(raw) == expected_hash:
            integrity_hits += 1
        compressed = compress_state_card_v0(raw, target_char_ratio=target_char_ratio)
        rt, ct = _token_count(raw), _token_count(compressed)
        savings.append(1.0 - (ct / rt) if rt else 0.0)
        jaccards.append(_jaccard(raw, compressed))

    integrity = integrity_hits / n if n else 0.0
    return {
        "schema": "saving_the_news_news_rt_bench_result_v1",
        "axis_id": "NEWS-RT",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "generated_at_utc": _utc_now(),
        "cohort_id": cohort_path.stem,
        "cohort_source": _display_path(cohort_path),
        "observation_row_count": n,
        "min_rows_required": min_rows,
        "measurement_status": "COMPLETE",
        "status": "OFFLINE_COHORT_BENCH",
        "ready_for_external_send": False,
        "compression_method": "state_card_unique_token_v0",
        "compression_params": {"target_char_ratio": target_char_ratio},
        "kpi": {
            "token_saving_ratio": round(statistics.mean(savings), 6),
            "jaccard_fidelity_proxy": round(statistics.mean(jaccards), 6),
            "integrity_score": round(integrity, 6),
            "latency_p99_ms": None,
            "notes": (
                "Offline news_observation cohort only. Not live stream. "
                "Not A-TRACK frozen-40 or LOGOS-CAP N240."
            ),
        },
        "kpi_distribution": {
            "token_saving_ratio_median": round(statistics.median(savings), 6),
            "jaccard_fidelity_proxy_min": round(min(jaccards), 6),
            "jaccard_fidelity_proxy_max": round(max(jaccards), 6),
        },
        "forbidden_interpretation": _forbidden(),
        "contract_ref": _display_path(CONTRACT) if CONTRACT.is_file() else None,
    }


def _forbidden() -> list[str]:
    return [
        "Not A-TRACK 47.5% or LOGOS-CAP 84.5% transfer.",
        "Not READY_FOR_NEWS_CLAIMS from news_benchmark_readiness.",
        "Not live breaking-news stream latency proof.",
    ]


def sync_contract_kpi(doc: dict[str, Any]) -> None:
    if not CONTRACT.is_file():
        return
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    kpi = doc.get("kpi") or {}
    contract["generated_at_utc"] = _utc_now()
    contract["measurement_status"] = doc.get("measurement_status", "NOT_MEASURED")
    if doc.get("measurement_status") == "COMPLETE":
        contract["status"] = "POC_COMPLETE"
    contract["kpi_slots"] = {
        "token_saving_ratio": kpi.get("token_saving_ratio"),
        "jaccard_fidelity_proxy": kpi.get("jaccard_fidelity_proxy"),
        "integrity_score": kpi.get("integrity_score"),
        "latency_p99_ms": kpi.get("latency_p99_ms"),
        "measured_at_utc": doc.get("generated_at_utc"),
        "cohort_id": doc.get("cohort_id"),
        "notes": str(kpi.get("notes", "")),
    }
    CONTRACT.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="NEWS-RT offline cohort bench")
    ap.add_argument("--cohort-jsonl", default=str(DEFAULT_COHORT))
    ap.add_argument("--min-rows", type=int, default=MIN_ROWS_DEFAULT)
    ap.add_argument("--target-char-ratio", type=float, default=0.55)
    ap.add_argument("--no-sync-contract", action="store_true")
    args = ap.parse_args()

    cohort = Path(args.cohort_jsonl)
    if not cohort.is_file():
        print(f"ERROR: missing cohort {_display_path(cohort)}", file=__import__("sys").stderr)
        return 2

    doc = run_bench(cohort, min_rows=args.min_rows, target_char_ratio=args.target_char_ratio)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.no_sync_contract:
        sync_contract_kpi(doc)

    print(
        f"Wrote {_display_path(OUT_JSON)} "
        f"status={doc['measurement_status']} rows={doc['observation_row_count']} "
        f"saving={doc['kpi'].get('token_saving_ratio')}"
    )
    return 0 if doc["measurement_status"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
