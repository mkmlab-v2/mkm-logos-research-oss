# -*- coding: utf-8 -*-
"""매크로 백테스트 스텁 v1: JSONL 출생 행 → `vector_4d_rule_school_v1` 집계·게이트 산출물.

선택적으로 행마다 숫자 ``label``이 있으면 해당 축과 Pearson/Spearman 상관을 계산한다(B-track·[HYPO]).
SciPy가 있으면 p-value를 채운다. 라벨이 없거나 2미만이면 상관 블록은 skipped.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "myeongri_rule_school_macro_stub_v1_latest.json"

_AXES = frozenset({"S", "L", "K", "M", "norm"})


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


def _rankdata(a: list[float]) -> list[float]:
    indexed = sorted(enumerate(a), key=lambda x: x[1])
    ranks = [0.0] * len(a)
    i = 0
    n = len(a)
    while i < n:
        j = i
        val = indexed[i][1]
        while j < n and indexed[j][1] == val:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            orig_idx = indexed[k][0]
            ranks[orig_idx] = avg_rank
        i = j
    return ranks


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx <= 0.0 or deny <= 0.0:
        return float("nan")
    return num / (denx * deny)


def _spearman_r(xs: list[float], ys: list[float]) -> float:
    return _pearson_r(_rankdata(xs), _rankdata(ys))


def _try_scipy_pvalues(
    xs: list[float], ys: list[float]
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    try:
        from scipy.stats import pearsonr, spearmanr

        pr = pearsonr(xs, ys)
        sr = spearmanr(xs, ys)
        pr_r = float(pr.statistic) if hasattr(pr, "statistic") else float(pr[0])
        pr_p = float(pr.pvalue) if hasattr(pr, "pvalue") else float(pr[1])
        sr_r = float(sr.statistic) if hasattr(sr, "statistic") else float(sr[0])
        sr_p = float(sr.pvalue) if hasattr(sr, "pvalue") else float(sr[1])
        return pr_r, pr_p, sr_r, sr_p
    except Exception:
        return None, None, None, None


def _axis_value(v: dict[str, Any], axis: str) -> float:
    if axis == "norm":
        s = float(v.get("S", 0.0))
        l = float(v.get("L", 0.0))
        k = float(v.get("K", 0.0))
        m = float(v.get("M", 0.0))
        return math.sqrt(s * s + l * l + k * k + m * m)
    return float(v.get(axis, 0.0))


def _extract_label(row: dict[str, Any]) -> Optional[float]:
    if "label" not in row:
        return None
    raw = row["label"]
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _label_correlation_block(
    pairs: list[tuple[float, float]], *, axis: str
) -> dict[str, Any]:
    if len(pairs) < 2:
        return {
            "status": "skipped",
            "skipped_reason": "insufficient_labeled_rows_need_at_least_2",
            "axis": axis,
            "n_label_pairs": len(pairs),
            "pearson_r": None,
            "spearman_r": None,
            "p_value_pearson": None,
            "p_value_spearman": None,
        }
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    pr = _pearson_r(xs, ys)
    sr = _spearman_r(xs, ys)
    spr = _try_scipy_pvalues(xs, ys)
    return {
        "status": "computed",
        "skipped_reason": None,
        "axis": axis,
        "n_label_pairs": len(pairs),
        "pearson_r": pr if pr == pr else None,
        "spearman_r": sr if sr == sr else None,
        "p_value_pearson": spr[1],
        "p_value_spearman": spr[3],
    }


def run_stub(rows: list[dict[str, Any]], *, label_axis: str = "L") -> dict[str, Any]:
    if label_axis not in _AXES:
        raise ValueError(f"label_axis must be one of {sorted(_AXES)}, got {label_axis!r}")

    fus = MyeongriCompleteFusion()
    acc = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    n = 0
    labeled_series: list[tuple[float, float]] = []

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
        lab = _extract_label(r)
        if lab is not None:
            labeled_series.append((lab, _axis_value(v, label_axis)))

    mean = {k: acc[k] / n for k in acc} if n else {k: 0.0 for k in acc}
    gate = "PASS" if n > 0 else "EMPTY"

    if not labeled_series:
        lc = {
            "status": "skipped",
            "skipped_reason": "no_numeric_labels_in_rows",
            "axis": label_axis,
            "n_label_pairs": 0,
            "pearson_r": None,
            "spearman_r": None,
            "p_value_pearson": None,
            "p_value_spearman": None,
        }
    else:
        lc = _label_correlation_block(labeled_series, axis=label_axis)

    return {
        "schema": "myeongri_rule_school_macro_stub_v1",
        "version": "1.1.0",
        "n_rows": n,
        "mean_vector_4d_rule_school_v1": mean,
        "gate": gate,
        "label_correlation": lc,
        "notes": "B-track optional label vs vector_4d_rule_school_v1 axis; not production gating.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in-jsonl", type=Path, required=True, help="birth rows: year,month,day,hour[,is_male,is_solar,label]")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--label-axis",
        default="L",
        choices=sorted(_AXES),
        help="4D key or norm for correlation when label is present",
    )
    args = ap.parse_args()
    rows = _parse_jsonl(args.in_jsonl)
    report = run_stub(rows, label_axis=args.label_axis)
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
