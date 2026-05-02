# -*- coding: utf-8 -*-
"""매크로 백테스트 스텁 v1: JSONL 출생 행 → `vector_4d_rule_school_v1` 집계·게이트 산출물.

라벨·상관은 미연동(B-track). 행 파싱·퓨전 결정론만 검증(exit code).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "myeongri_rule_school_macro_stub_v1_latest.json"


def _parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError("each JSONL line must be an object")
        rows.append(obj)
    return rows


def run_stub(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fus = MyeongriCompleteFusion()
    acc = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    n = 0
    for r in rows:
        doc = fus.calculate_complete_fusion(
            int(r["year"]),
            int(r["month"]),
            int(r["day"]),
            int(r["hour"]),
            is_solar=bool(r.get("is_solar", False)),
            is_male=bool(r.get("is_male", True)),
        )
        v = doc.get("vector_4d_rule_school_v1") or {}
        for k in acc:
            acc[k] += float(v.get(k, 0.0))
        n += 1
    mean = {k: acc[k] / n for k in acc} if n else {k: 0.0 for k in acc}
    gate = "PASS" if n > 0 else "EMPTY"
    return {
        "schema": "myeongri_rule_school_macro_stub_v1",
        "version": "1.0.0",
        "n_rows": n,
        "mean_vector_4d_rule_school_v1": mean,
        "gate": gate,
        "notes": "label_correlation_not_implemented_v1",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-jsonl", type=Path, required=True, help="birth rows: year,month,day,hour[,is_male,is_solar]")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    rows = _parse_jsonl(args.in_jsonl)
    report = run_stub(rows)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["gate"] == "EMPTY":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
