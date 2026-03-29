#!/usr/bin/env python3
"""
CI integrity guard (draft): verifies frozen artifacts from anchor 45563d4bfd.

Checks:
  - Four-way intersection JSON: SHA-256, count_all_four, list length, per-regime k=6866
  - MASTER_PROBE_v1_ACTUAL.json matches golden snapshot (byte identity or SHA-256)
  - scripts/verify_master_probe_all_states.py exit 0 and report checks_total / all_pass

Usage:
  py scripts/integrity_guard.py

Exit: 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return json.loads(raw.decode("utf-8"))


def _fail(msg: str) -> int:
    print(f"INTEGRITY_FAIL: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    root = _repo_root()
    lock_path = root / "tests" / "snapshots" / "integrity_lock.json"
    if not lock_path.is_file():
        return _fail(f"missing lock file {lock_path}")

    lock = _load_json(lock_path)
    k_top = int(lock["k_top"])
    per_regime = lock.get("per_regime_top_k", {})

    # --- Intersection artifact ---
    inter_meta = lock["intersection"]
    inter_path = root / inter_meta["relative_path"]
    if not inter_path.is_file():
        return _fail(f"intersection file missing: {inter_path}")

    got_hash = _sha256_file(inter_path)
    if got_hash != inter_meta["sha256"]:
        return _fail(
            f"intersection SHA256 mismatch: expected {inter_meta['sha256']}, got {got_hash}"
        )

    inter_data = _load_json(inter_path)
    if inter_data.get("count_all_four") != inter_meta["count_all_four"]:
        return _fail(
            f"count_all_four expected {inter_meta['count_all_four']}, got {inter_data.get('count_all_four')}"
        )
    ids = inter_data.get("intersection_all_four_verse_ids", [])
    if len(ids) != inter_meta["intersection_list_length"]:
        return _fail(
            f"intersection list length expected {inter_meta['intersection_list_length']}, got {len(ids)}"
        )

    counts = inter_data.get("counts") or {}
    for regime, expected_k in per_regime.items():
        if int(counts.get(regime, -1)) != int(expected_k):
            return _fail(
                f"counts[{regime}] expected {expected_k}, got {counts.get(regime)}"
            )
    if int(k_top) != 6866:
        return _fail(f"lock k_top mismatch (expected 6866 in lock file)")

    # --- ACTUAL vs golden snapshot ---
    mp = lock["master_probe"]
    actual_path = root / mp["actual_relative_path"]
    golden_path = root / mp["golden_relative_path"]
    if not actual_path.is_file():
        return _fail(f"ACTUAL missing: {actual_path}")
    if not golden_path.is_file():
        return _fail(f"golden snapshot missing: {golden_path}")

    actual_hash = _sha256_file(actual_path)
    golden_hash = _sha256_file(golden_path)
    if actual_hash != golden_hash:
        return _fail(
            f"ACTUAL vs golden SHA256 differ: actual={actual_hash}, golden={golden_hash}"
        )
    if golden_hash != mp["golden_sha256"]:
        return _fail(
            f"golden file SHA256 mismatch lock: expected {mp['golden_sha256']}, got {golden_hash}"
        )

    # Byte-for-byte (redundant if hashes match)
    if actual_path.read_bytes() != golden_path.read_bytes():
        return _fail("ACTUAL and golden bytes differ despite matching hashes (unexpected)")

    # --- Master probe verifier subprocess ---
    verify_script = root / "scripts" / "verify_master_probe_all_states.py"
    default_probe = root / mp["default_probe_relative_path"]
    if not verify_script.is_file():
        return _fail(f"missing {verify_script}")
    if not default_probe.is_file():
        return _fail(f"missing default probe {default_probe}")

    proc = subprocess.run(
        [sys.executable, str(verify_script), str(default_probe)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "").strip()
    if out.startswith("\ufeff"):
        out = out.lstrip("\ufeff")

    try:
        report = json.loads(out)
    except json.JSONDecodeError as e:
        return _fail(f"verify_master_probe JSON parse error: {e}; stderr={proc.stderr!r}")

    agg = report.get("aggregate") or {}
    summ = report.get("summary") or {}
    checks_total = int(agg.get("checks_total", -1))
    all_pass = bool(summ.get("all_pass"))

    exp_total = int(mp["checks_total_expected"])
    if checks_total != exp_total:
        return _fail(f"checks_total expected {exp_total}, got {checks_total}")
    if all_pass != mp["all_pass_expected"]:
        return _fail(f"all_pass expected {mp['all_pass_expected']}, got {all_pass}")
    if proc.returncode != 0:
        return _fail(f"verify_master_probe exit {proc.returncode}")

    print(
        json.dumps(
            {
                "status": "ok",
                "anchor_commit_short": lock.get("anchor_commit_short"),
                "k_top": k_top,
                "count_all_four": inter_meta["count_all_four"],
                "checks_total": checks_total,
                "all_pass": all_pass,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
