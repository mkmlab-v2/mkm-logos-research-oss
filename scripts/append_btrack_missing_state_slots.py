"""
One-shot: append B-track rows for state_id 1–3 and 5–15 to today's
myeongni_16_state_experiment_YYYYMMDD.jsonl (skip state_ids already present).

Vectors: neutral→v4 blend for 1–3 (factor sid/4); v4↔v16 for 5–15 (t=(sid-4)/12).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

import myeongni_16_state_experiment_ledger as ledger  # noqa: E402

V4 = {"S": 0.92, "L": 0.08, "K": 0.95, "M": 0.05}
V16 = {"S": 0.05, "L": 0.95, "K": 0.08, "M": 0.92}
NEUTRAL = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}

TARGET_SIDS = list(range(1, 4)) + list(range(5, 16))


def _lerp(a: dict[str, float], b: dict[str, float], t: float) -> dict[str, float]:
    return {k: round((1.0 - t) * a[k] + t * b[k], 2) for k in a}


def vector_for(sid: int) -> dict[str, float]:
    if sid in (1, 2, 3):
        return _lerp(NEUTRAL, V4, sid / 4.0)
    if 5 <= sid <= 15:
        t = (sid - 4) / 12.0
        return _lerp(V4, V16, t)
    raise ValueError(f"unexpected sid {sid}")


def existing_state_ids(path: Path) -> set[int]:
    if not path.is_file():
        return set()
    out: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        sid = obj.get("state_id")
        if isinstance(sid, int):
            out.add(sid)
    return out


def main() -> int:
    root = _ROOT
    now = datetime.now(timezone.utc)
    daily = root / ledger.WORKSPACE_DATA_REL / f"{ledger.LEDGER_PREFIX}_{now.strftime('%Y%m%d')}.jsonl"
    have = existing_state_ids(daily)
    base_ts = datetime(2026, 3, 29, 14, 0, 0, tzinfo=timezone.utc)
    sec = 0
    appended = 0
    for sid in TARGET_SIDS:
        if sid in have:
            continue
        ts = (base_ts + timedelta(seconds=sec)).isoformat()
        sec += 60
        rec = {
            "ts_utc": ts,
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "stub": False,
            "state_id": sid,
            "vector_4d": vector_for(sid),
            "note": (
                f"B-track state_id={sid}; "
                + ("neutral→GY_L4_PEAK blend (factor sid/4)" if sid <= 3 else "GY_L4_PEAK↔TY_L4_PEAK blend (t=(sid-4)/12)")
            ),
        }
        ledger.append_myeongni_16_state_experiment(root, rec, set_ts_if_missing=False)
        appended += 1
        print(f"appended state_id={sid} -> {daily.name}")
    print(f"done: appended {appended} row(s); file={daily}")
    n = ledger.validate_jsonl_file(daily)
    print(f"validate_jsonl_file: {n} line(s) OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
