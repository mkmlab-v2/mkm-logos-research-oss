#!/usr/bin/env python3
"""Build B-track stress lanes for Universal Matrix (server log, EN tech, finance alnum).

Never writes Track A golden or active report. Output: lane eval JSON files + optional
MULTILENS_LARGE_STRESS_V1.json pointer (case manifest summary only).
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

LANE_SPECS: dict[str, dict[str, Any]] = {
    "server_log_stress_v1": {
        "domain_tag": "server_log_stress",
        "domain": "server_log_stress",
        "id_prefix": "srvlog",
        "description": "Synthetic + template server/nginx/app logs (special-char dense).",
    },
    "en_tech_spec_stress_v1": {
        "domain_tag": "en_tech_spec_stress",
        "domain": "en_tech_spec_stress",
        "id_prefix": "entech",
        "description": "English-only API/infra spec paragraphs (41k OOV stress).",
    },
    "finance_alnum_dense_v1": {
        "domain_tag": "finance_alnum_dense",
        "domain": "finance_alnum_dense",
        "id_prefix": "finalg",
        "description": "Alphanumeric-dense finance/ticker/metrics blocks.",
    },
}

LOG_TEMPLATES = [
    '{ts} [{level}] {svc} req_id={rid} method={meth} path="{path}" status={st} latency_ms={ms} ua="{ua}"',
    "{ts} ERROR com.example.worker partition={p} offset={off} exception={exc} retry={n}",
    '127.0.0.1 - - [{ts}] "{meth} {path} HTTP/1.1" {st} {bytes} "-" "curl/8.4.0"',
    "{ts} WARN kafka.consumer group=mkm-ops topic=audit lag={lag} rebalance=IN_PROGRESS",
]

TECH_PARAS = [
    (
        "The compression gateway MUST expose `POST /v1/metering/log` with idempotent "
        "keys; clients SHOULD retry with exponential backoff when `503` or "
        "`429` is returned. Payload schema version `multilens_performance_eval_input_v1` "
        "remains backward compatible for twelve months."
    ),
    (
        "Shard router selects `zone_c_hangul`, `zone_a_scm`, or `zone_d_ssot` using "
        "token histogram features; mis-routed documents inflate Jaccard loss without "
        "triggering parse errors. Integration tests require frozen golden forty cases."
    ),
    (
        "Kubernetes liveness probes hit `/healthz` every ten seconds; readiness waits "
        "until SQLite migration `20260521_universal_matrix` completes. Memory limit "
        "2Gi; CPU request 500m — do not co-locate with GPU inference pods."
    ),
]

FINANCE_TEMPLATES = [
    "KOSPI {idx} {chg:+.2f}% | volume {vol}M | foreign net {fnet:+,} | program {prog:+,} | VIX proxy {vix:.1f}",
    "BTC-USD ${px:,.0f} 24h {chg:+.2f}% funding {fund:.4f}% OI {oi:.2f}B basis {basis:+.2f}%",
    "Ticker {sym} EPS {eps:.2f} P/E {pe:.1f}x EV/EBITDA {ev:.1f}x FCF yield {fcf:.1f}% guidance {guid}",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shorten(text: str, ratio: float = 0.55) -> str:
    words = text.split()
    if not words:
        return text
    keep = max(1, int(len(words) * ratio))
    return " ".join(words[:keep])


def _case(
    *,
    cid: str,
    raw: str,
    domain: str,
    source: str,
) -> dict[str, Any]:
    comp = _shorten(raw)
    return {
        "id": cid,
        "raw_text": raw,
        "compressed_text": comp,
        "reconstructed_text": comp,
        "domain": domain,
        "source_path": source,
    }


def _gen_log_cases(n: int, rng: random.Random) -> list[dict[str, Any]]:
    levels = ("INFO", "WARN", "ERROR", "DEBUG")
    services = ("nginx", "api-gw", "worker", "scheduler", "mkm-compress")
    paths = ("/v1/compress", "/healthz", "/metrics", "/debug/pprof", "/api/v2/report")
    out: list[dict[str, Any]] = []
    for i in range(n):
        tpl = rng.choice(LOG_TEMPLATES)
        raw = tpl.format(
            ts="2026-06-03T08:15:32.481Z",
            level=rng.choice(levels),
            svc=rng.choice(services),
            rid=f"{rng.randint(100000, 999999):x}",
            meth=rng.choice(("GET", "POST", "PUT", "PATCH")),
            path=rng.choice(paths),
            st=rng.choice((200, 201, 400, 401, 429, 500, 502)),
            ms=rng.randint(1, 4500),
            ua="Mozilla/5.0 (compatible; MKMStress/1.0)",
            p=rng.randint(0, 11),
            off=rng.randint(0, 999999),
            exc=rng.choice(("TimeoutError", "JSONDecodeError", "ConnectionResetError")),
            n=rng.randint(0, 5),
            bytes=rng.randint(128, 65536),
            lag=rng.randint(0, 5000),
        )
        raw += " | trace_id=" + "".join(rng.choice("0123456789abcdef") for _ in range(32))
        out.append(
            _case(
                cid=f"srvlog_{i+1:04d}",
                raw=raw,
                domain="server_log_stress",
                source="scripts/build_multilens_large_stress_lanes_v1.py#log_synthetic",
            )
        )
    return out


def _gen_tech_cases(n: int, rng: random.Random) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(n):
        base = rng.choice(TECH_PARAS)
        extra = (
            f" Revision {rng.randint(1, 99)}: checksum sha256:"
            f"{''.join(rng.choice('0123456789abcdef') for _ in range(64))}."
        )
        raw = base + extra
        out.append(
            _case(
                cid=f"entech_{i+1:04d}",
                raw=raw,
                domain="en_tech_spec_stress",
                source="scripts/build_multilens_large_stress_lanes_v1.py#en_tech_synthetic",
            )
        )
    return out


def _gen_finance_cases(n: int, rng: random.Random) -> list[dict[str, Any]]:
    syms = ("005930", "000660", "AAPL", "MSFT", "BTC", "ETH", "KOSPI", "NDX")
    out: list[dict[str, Any]] = []
    for i in range(n):
        tpl = rng.choice(FINANCE_TEMPLATES)
        raw = tpl.format(
            idx=rng.randint(2400, 2900),
            chg=rng.uniform(-4.5, 4.5),
            vol=rng.randint(100, 900),
            fnet=rng.randint(-500, 500) * 1_000_000,
            prog=rng.randint(-300, 300) * 1_000_000,
            vix=rng.uniform(12.0, 35.0),
            px=rng.uniform(25000, 120000),
            fund=rng.uniform(-0.02, 0.03),
            oi=rng.uniform(0.5, 3.0),
            basis=rng.uniform(-0.5, 0.5),
            sym=rng.choice(syms),
            eps=rng.uniform(0.5, 12.0),
            pe=rng.uniform(8.0, 45.0),
            ev=rng.uniform(5.0, 25.0),
            fcf=rng.uniform(1.0, 8.0),
            guid=rng.choice(("inline", "below", "above", "withdrawn")),
        )
        raw += f" | row={i+1} bench=large_stress_v1"
        out.append(
            _case(
                cid=f"finalg_{i+1:04d}",
                raw=raw,
                domain="finance_alnum_dense",
                source="scripts/build_multilens_large_stress_lanes_v1.py#finance_synthetic",
            )
        )
    return out


def _harvest_stateless_jsonl(path: Path, *, max_rows: int, id_prefix: str, domain: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = str(row.get("text") or row.get("content") or row.get("body") or "").strip()
            if len(text) < 80:
                continue
            out.append(
                _case(
                    cid=f"{id_prefix}_jsonl_{len(out)+1:04d}",
                    raw=text[:8000],
                    domain=domain,
                    source=str(path.relative_to(ROOT)).replace("\\", "/"),
                )
            )
            if len(out) >= max_rows:
                break
    return out


def _write_lane(
    lane_id: str,
    cases: list[dict[str, Any]],
    *,
    out_dir: Path,
    domain_tag: str | None = None,
    description: str | None = None,
) -> Path:
    spec = LANE_SPECS.get(lane_id) or {
        "domain_tag": domain_tag or lane_id,
        "domain": domain_tag or lane_id,
        "description": description or f"Stress lane {lane_id}",
    }
    out_path = out_dir / f"universal_compression_bench_lane_{lane_id}.json"
    doc = {
        "schema": "multilens_performance_eval_input_v1",
        "description": spec["description"],
        "research_only": True,
        "boundary_ack": "B-track [HYPO] large stress — not Track A; not MS headline",
        "compression_cases": cases,
        "domain_tag": spec["domain_tag"],
        "lane_id": lane_id,
        "generated_at_utc": _utc(),
        "stress_tier": "multilens_large_stress_v1",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-lane", type=int, default=120, help="Synthetic cases per stress lane.")
    ap.add_argument("--seed", type=int, default=20260603)
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl",
        help="Optional extra harvest (enterprise structured PoC).",
    )
    ap.add_argument("--jsonl-max", type=int, default=40, help="Max rows from --jsonl into enterprise lane.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "docs/final/artifacts",
    )
    ap.add_argument(
        "--write-pointer",
        action="store_true",
        help="Write docs/final/artifacts/MULTILENS_LARGE_STRESS_V1.json lane pointer.",
    )
    args = ap.parse_args()

    rng = random.Random(args.seed)
    n = max(1, args.per_lane)
    generators = {
        "server_log_stress_v1": lambda: _gen_log_cases(n, rng),
        "en_tech_spec_stress_v1": lambda: _gen_tech_cases(n, rng),
        "finance_alnum_dense_v1": lambda: _gen_finance_cases(n, rng),
    }
    stats: list[dict[str, Any]] = []
    total = 0
    for lane_id, gen in generators.items():
        cases = gen()
        path = _write_lane(lane_id, cases, out_dir=args.out_dir)
        stats.append({"lane_id": lane_id, "cases": len(cases), "path": str(path.relative_to(ROOT)).replace("\\", "/")})
        total += len(cases)

    jsonl_extra: list[dict[str, Any]] = []
    if args.jsonl_max > 0:
        jsonl_extra = _harvest_stateless_jsonl(
            (ROOT / args.jsonl).resolve() if not args.jsonl.is_absolute() else args.jsonl,
            max_rows=args.jsonl_max,
            id_prefix="ent_jsonl",
            domain="enterprise_general",
        )
    if jsonl_extra:
        ent_path = args.out_dir / "universal_compression_bench_lane_enterprise_jsonl_stress_v1.json"
        _write_lane(
            "enterprise_jsonl_stress_v1",
            jsonl_extra,
            out_dir=args.out_dir,
            domain_tag="enterprise_general",
            description="Harvest from stateless PoC JSONL (structured enterprise stress).",
        )
        stats.append(
            {
                "lane_id": "enterprise_jsonl_stress_v1",
                "cases": len(jsonl_extra),
                "path": str(ent_path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
        total += len(jsonl_extra)

    if args.write_pointer:
        ptr = {
            "schema": "multilens_large_stress_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "track_wall": "B-track — no Track A active write",
            "case_count": total,
            "lanes": stats,
            "registry_merge_note": "Enable lanes in universal_compression_bench_matrix_registry_v1.json",
        }
        ptr_path = args.out_dir / "MULTILENS_LARGE_STRESS_V1.json"
        ptr_path.write_text(json.dumps(ptr, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"stress_lanes": stats, "total_cases": total}, ensure_ascii=False))
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
