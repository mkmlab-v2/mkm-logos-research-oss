#!/usr/bin/env python3
"""Universal Root contributor shard bench — validate + canonical overlap check (local only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/universal_root_contributor_bench_v1_latest.json"
CANONICAL = ROOT / "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json"
VALIDATE = ROOT / "scripts/validate_universal_root_contributor_fixture_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _load_canonical_primes() -> set[str]:
    if not CANONICAL.is_file():
        return set()
    doc = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))
    samples = doc.get("samples") or []
    return {str(s.get("prime_en")).strip() for s in samples if isinstance(s, dict) and s.get("prime_en")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shard", type=Path, required=True)
    ap.add_argument("--min-rows", type=int, default=3)
    ap.add_argument("--max-rows", type=int, default=50)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    shard = args.shard.resolve()
    if not shard.is_file():
        raise SystemExit(f"shard missing: {shard}")

    validate_cmd = [
        PY,
        str(VALIDATE),
        "--json",
        str(shard),
        "--min-rows",
        str(args.min_rows),
        "--max-rows",
        str(args.max_rows),
    ]
    proc = subprocess.run(validate_cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    validate_tail = ((proc.stdout or "") + (proc.stderr or "")).strip()[-400:]
    validate_ok = proc.returncode == 0

    overlap: list[str] = []
    warnings: list[str] = []
    sample_count = 0
    if validate_ok:
        doc = json.loads(shard.read_text(encoding="utf-8-sig"))
        samples = doc.get("samples") or []
        sample_count = len(samples) if isinstance(samples, list) else 0
        canonical = _load_canonical_primes()
        contrib_primes = [
            str(s.get("prime_en")).strip()
            for s in samples
            if isinstance(s, dict) and s.get("prime_en")
        ]
        overlap = sorted(set(contrib_primes) & canonical)
        if overlap:
            warnings.append(
                f"prime_en overlap with canonical 500 fixture ({len(overlap)}): maintainer review required"
            )
        dup = sorted({p for p in contrib_primes if contrib_primes.count(p) > 1})
        if dup:
            warnings.append(f"duplicate prime_en within shard: {dup}")

    ok = validate_ok
    report: dict[str, Any] = {
        "schema": "universal_root_contributor_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "telemetry": False,
        "shard": _rel(shard),
        "sample_count": sample_count,
        "validate_ok": validate_ok,
        "validate_cmd": validate_cmd,
        "validate_tail": validate_tail,
        "canonical_overlap_primes": overlap,
        "warnings": warnings,
        "topology_crosswalk_on_shard": "not_run_v1_stub",
        "ok": ok,
        "reproduce": f"py scripts/run_universal_root_contributor_bench_v1.py --shard {_rel(shard)}",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "validate_ok": validate_ok, "overlap": len(overlap), "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
