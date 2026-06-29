#!/usr/bin/env python3
"""Diagnose sparse sidecar → Logos OOS active-day count (KOSPI 252d tail). research_only."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_sparse_sidecar_coverage_diagnostic_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _myeongni_sign(sidecar_row: dict[str, Any] | None) -> int:
    if not sidecar_row:
        return 0
    dated = sidecar_row.get("dated_source_snapshots_asof_eval_date") or {}
    mt = (((dated.get("myeongni_16_state_jsonl") or {}).get("snapshot")) or {}).get("mapping_target")
    m = str(mt or "neutral").strip().lower()
    if m == "bull":
        return 1
    if m == "bear":
        return -1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_prophecy_score_30y_dual_latest.json")
    ap.add_argument("--sidecar-json", type=Path, required=True)
    ap.add_argument("--instrument", default="kospi")
    ap.add_argument("--oos-tail-days", type=int, default=252)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score = _read(args.score_json)
    sidecar = _read(args.sidecar_json)
    inst = args.instrument.strip().lower()
    panel = [
        r
        for r in (score.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == inst
    ]
    panel.sort(key=lambda x: str(x.get("eval_date") or ""))
    oos = panel[-args.oos_tail_days :]
    train = panel[: -args.oos_tail_days]

    by_ed = {
        str(r.get("eval_date") or "")[:10]: r
        for r in (sidecar.get("per_date_features") or [])
        if isinstance(r, dict)
    }
    aux = sidecar.get("dated_jsonl_aux_sources") or {}

    def _split_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
        mt_c: Counter[str] = Counter()
        sig = 0
        missing = 0
        for r in rows:
            ed = str(r.get("eval_date") or "")[:10]
            sr = by_ed.get(ed)
            if not sr:
                missing += 1
                mt_c["no_sidecar_row"] += 1
                continue
            dated = (sr.get("dated_source_snapshots_asof_eval_date") or {}).get("myeongni_16_state_jsonl")
            if not dated or not (dated.get("snapshot")):
                mt_c["no_jsonl_snapshot"] += 1
            else:
                mt = str((dated.get("snapshot") or {}).get("mapping_target") or "neutral").lower()
                mt_c[mt] += 1
            if _myeongni_sign(sr) != 0:
                sig += 1
        return {
            "n_days": len(rows),
            "sidecar_row_missing": missing,
            "myeongni_nonzero_sign_days": sig,
            "mapping_target_counts": dict(mt_c),
        }

    out = {
        "schema": "logos_sparse_sidecar_coverage_diagnostic_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
            "sidecar_json": str(args.sidecar_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/"),
            "instrument": inst,
            "oos_tail_days": args.oos_tail_days,
            "dated_jsonl_aux_sources": aux,
        },
        "train_window": _split_stats(train),
        "oos_window": _split_stats(oos),
        "interpretation_ko": [
            "train n_active=0 은 sidecar_only에서 train 구간 bull/bear 스냅샷이 거의 없을 때 흔함(파라미터는 sig_days·-neutral_size로 선택).",
            "OOS active 일수는 라우터가 명리 sidecar sign≠0 인 날만 카운트(252d KOSPI 기준).",
            "golden 0.565 재현은 target_instrument=kospi + 30y score + sparse(202604) sidecar 조합을 우선 확인.",
        ],
    }
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
