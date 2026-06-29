#!/usr/bin/env python3
"""P3 Merkle audit micro-bench — weak header/footer gate vs Merkle verify (B-track).

Neural plane: token stream may be tampered (simulated).
Raw gate: header+footer+length only (weak — misses mid-stream edits).
Post audit: SHA-256 Merkle root verify (symbolic plane).

Dual-report — collapsed_combined_score stays null.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE = ROOT / "tests/fixtures/dual_plane_p3_merkle_audit_crosswalk_v1.json"
DEFAULT_OUT = ROOT / "reports/dual_plane_p3_merkle_audit_micro_bench_v1_latest.json"
SCHEMA = "dual_plane_p3_merkle_audit_micro_bench_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _leaf(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def merkle_root(tokens: list[str]) -> str:
    if not tokens:
        return hashlib.sha256(b"").hexdigest()
    layer = [_leaf(t) for t in tokens]
    while len(layer) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else layer[i]
            nxt.append(hashlib.sha256(left + right).digest())
        layer = nxt
    return layer[0].hex()


def apply_tamper(sample: dict[str, Any]) -> list[str]:
    tokens = list(sample.get("canonical_tokens") or [])
    if not sample.get("tampered"):
        return tokens
    mode = sample.get("tamper_mode")
    if mode == "append":
        return tokens + [str(sample.get("tamper_value", "X"))]
    idx = int(sample.get("tamper_index", 0))
    val = str(sample.get("tamper_value", "X"))
    if 0 <= idx < len(tokens):
        out = tokens[:]
        out[idx] = val
        return out
    return tokens + [val]


def weak_raw_passes(stream: list[str], canonical: list[str]) -> bool:
    """Weak neural-side gate: length + head/tail only (intentionally unsafe)."""
    if len(stream) != len(canonical):
        return False
    if not stream:
        return True
    return stream[0] == canonical[0] and stream[-1] == canonical[-1]


def merkle_post_passes(stream: list[str], canonical: list[str]) -> bool:
    return merkle_root(stream) == merkle_root(canonical)


def run_bench(fixture: dict[str, Any]) -> dict[str, Any]:
    if fixture.get("schema") != "dual_plane_p3_merkle_audit_crosswalk_v1":
        raise ValueError("fixture schema mismatch")

    rows: list[dict[str, Any]] = []
    raw_undetected_tamper = 0
    post_undetected_tamper = 0
    tamper_count = 0
    clean_raw_fail = 0
    clean_post_fail = 0
    clean_count = 0

    for s in fixture.get("samples") or []:
        if not isinstance(s, dict):
            continue
        canonical = list(s.get("canonical_tokens") or [])
        stream = apply_tamper(s)
        is_tampered = bool(s.get("tampered"))

        raw_ok = weak_raw_passes(stream, canonical)
        post_ok = merkle_post_passes(stream, canonical)

        if is_tampered:
            tamper_count += 1
            if raw_ok:
                raw_undetected_tamper += 1
            if not post_ok:
                pass  # detected
            else:
                post_undetected_tamper += 1
        else:
            clean_count += 1
            if not raw_ok:
                clean_raw_fail += 1
            if not post_ok:
                clean_post_fail += 1

        rows.append(
            {
                "id": s.get("id"),
                "tampered": is_tampered,
                "stream_len": len(stream),
                "raw_weak_pass": raw_ok,
                "post_merkle_pass": post_ok,
            }
        )

    n = len(rows)
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "row_count": n,
        "metrics": {
            "raw_tamper_undetected_rate": round(
                (raw_undetected_tamper / tamper_count) if tamper_count else 0.0, 4
            ),
            "post_merkle_tamper_undetected_rate": round(
                (post_undetected_tamper / tamper_count) if tamper_count else 0.0, 4
            ),
            "post_merkle_tamper_detect_rate": round(
                1.0 - ((post_undetected_tamper / tamper_count) if tamper_count else 0.0), 4
            ),
            "clean_raw_pass_rate": round(
                1.0 - ((clean_raw_fail / clean_count) if clean_count else 0.0), 4
            ),
            "clean_post_pass_rate": round(
                1.0 - ((clean_post_fail / clean_count) if clean_count else 0.0), 4
            ),
            "collapsed_combined_score": None,
        },
        "rows": rows,
        "lane_note": "Separate from Universal Root OSS hero — FAIL-COMP-004",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--timing-iterations", type=int, default=50)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    fixture_path = args.fixture.resolve()
    fixture = json.loads(fixture_path.read_text(encoding="utf-8-sig"))

    t0 = time.perf_counter()
    report = run_bench(fixture)
    single_ms = (time.perf_counter() - t0) * 1000.0

    times: list[float] = []
    for _ in range(max(1, args.timing_iterations)):
        t1 = time.perf_counter()
        run_bench(fixture)
        times.append((time.perf_counter() - t1) * 1000.0)
    times.sort()
    p95 = times[min(len(times) - 1, int(len(times) * 0.95))]

    report["metrics"]["bench_wall_ms_single"] = round(single_ms, 4)
    report["metrics"]["bench_wall_ms_p95"] = round(p95, 4)
    report["fixture"] = _rel(fixture_path)
    report["reproduce"] = f"py scripts/run_dual_plane_p3_merkle_audit_micro_bench_v1.py --fixture {_rel(fixture_path)}"
    report["ok"] = (
        report["metrics"]["post_merkle_tamper_undetected_rate"] == 0.0
        and report["metrics"]["clean_post_pass_rate"] == 1.0
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "raw_tamper_undetected_rate": report["metrics"]["raw_tamper_undetected_rate"],
                "post_merkle_tamper_undetected_rate": report["metrics"]["post_merkle_tamper_undetected_rate"],
                "bench_wall_ms_p95": report["metrics"]["bench_wall_ms_p95"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
