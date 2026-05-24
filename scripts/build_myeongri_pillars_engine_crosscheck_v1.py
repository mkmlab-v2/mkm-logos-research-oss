#!/usr/bin/env python3
"""Cross-check locked_eval golden vs live engine vs LoRA predictions (no GPU)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_deterministic_lora_golden_views_v1 import pillars_view  # noqa: E402
from scripts.prep_myeongri_deterministic_lora_golden_v1 import _build_body  # noqa: E402

DEFAULT_GOLDEN = ROOT / "data/training/myeongri_deterministic_lora_golden_bulk_v1/locked_eval.jsonl"
DEFAULT_PRED = ROOT / "reports/myeongri_deterministic_lora_locked_eval_predictions_latest.jsonl"
DEFAULT_MISMATCH = ROOT / "reports/myeongri_pillars_mismatch_sample_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/myeongri_pillars_engine_crosscheck_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_golden(path: Path) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["sample_id"])] = row
    return rows


def _load_predictions(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        out[str(o["id"])] = o
    return out


def _saju_tuple(view: dict) -> tuple[str, str, str, str] | None:
    saju = (view.get("full_saju") or {}).get("saju") or {}
    if not isinstance(saju, dict):
        return None
    keys = ("year", "month", "day", "hour")
    if not all(saju.get(k) for k in keys):
        return None
    return tuple(str(saju[k]) for k in keys)


def _classify(
    *,
    gold_p: dict,
    engine_p: dict,
    pred_p: dict,
) -> str:
    g = _saju_tuple(gold_p)
    e = _saju_tuple(engine_p)
    p = _saju_tuple(pred_p)
    if g and e and g == e:
        if p == g:
            return "model_matches_golden_and_engine"
        if p and p != g:
            if p == ("계묘", "임자", "신사", "기미") or p[0] == "계묘" and p[2] == "신사":
                return "model_mode_collapse_while_golden_ok"
            return "model_wrong_pillars_golden_ok"
        return "model_unparseable_or_empty"
    if g and e and g != e:
        return "golden_engine_drift"
    return "insufficient_data"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden-jsonl", type=Path, default=DEFAULT_GOLDEN)
    ap.add_argument("--predictions-jsonl", type=Path, default=DEFAULT_PRED)
    ap.add_argument("--mismatch-json", type=Path, default=DEFAULT_MISMATCH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sample-limit", type=int, default=0, help="0 = all locked_eval rows")
    ap.add_argument(
        "--all-locked-eval",
        action="store_true",
        help="Analyze every row in --golden-jsonl (ignore mismatch sample list).",
    )
    args = ap.parse_args()

    if not args.golden_jsonl.is_file():
        print(f"missing golden: {args.golden_jsonl}", file=sys.stderr)
        return 2
    if not args.predictions_jsonl.is_file():
        print(f"missing predictions: {args.predictions_jsonl}", file=sys.stderr)
        return 2

    golden_rows = _load_golden(args.golden_jsonl)
    preds = _load_predictions(args.predictions_jsonl)

    sample_ids: list[str]
    if args.all_locked_eval:
        sample_ids = sorted(golden_rows.keys())
    elif args.mismatch_json.is_file():
        mobj = json.loads(args.mismatch_json.read_text(encoding="utf-8"))
        sample_ids = [s["sample_id"] for s in mobj.get("mismatch_samples") or []]
    else:
        sample_ids = list(golden_rows.keys())

    if args.sample_limit > 0:
        sample_ids = sample_ids[: args.sample_limit]

    if not sample_ids:
        sample_ids = sorted(golden_rows.keys())
        if args.sample_limit > 0:
            sample_ids = sample_ids[: args.sample_limit]

    cases: list[dict] = []
    classes: Counter[str] = Counter()

    for sid in sample_ids:
        row = golden_rows.get(sid)
        if not row:
            continue
        utc = str(row.get("birth_instant_utc") or "")
        tz = str(row.get("iana_tz") or "")
        male = bool(row.get("is_male"))
        gold_exp = row["expected_result"]
        engine_body = _build_body(utc, tz, male)
        gold_p = pillars_view(gold_exp)
        engine_p = pillars_view(engine_body)

        pred_raw = preds.get(sid, {})
        pred_n: dict = {}
        if pred_raw.get("parse_ok"):
            try:
                pred_n = json.loads(pred_raw.get("prediction") or "{}")
            except json.JSONDecodeError:
                pred_n = {}
        pred_p = pillars_view(pred_n) if pred_n else {}

        cls = _classify(gold_p=gold_p, engine_p=engine_p, pred_p=pred_p)
        classes[cls] += 1

        cases.append(
            {
                "sample_id": sid,
                "classification": cls,
                "birth_instant_utc": utc,
                "iana_tz": tz,
                "is_male": male,
                "golden_saju": (gold_p.get("full_saju") or {}).get("saju"),
                "engine_saju": (engine_p.get("full_saju") or {}).get("saju"),
                "predicted_saju": (pred_p.get("full_saju") or {}).get("saju"),
                "golden_local_iso": (gold_p.get("resolution") or {}).get("local_iso"),
                "engine_local_iso": (engine_p.get("resolution") or {}).get("local_iso"),
                "predicted_local_iso": (pred_p.get("resolution") or {}).get("local_iso"),
                "golden_matches_engine": _saju_tuple(gold_p) == _saju_tuple(engine_p),
            }
        )

    n = len(cases)
    gold_engine_ok = sum(1 for c in cases if c["golden_matches_engine"])
    doc = {
        "schema": "myeongri_pillars_engine_crosscheck_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "rows_analyzed": n,
        "golden_matches_engine_count": gold_engine_ok,
        "golden_matches_engine_rate": round(gold_engine_ok / n, 6) if n else 0.0,
        "classification_counts": dict(classes),
        "recommendations_ko": [],
        "cases": cases,
        "track_wall": {"a_track_auto_promotion": False, "ready_for_external_send": False},
    }

    rec: list[str] = []
    if gold_engine_ok == n and n:
        rec.append(
            "골든 expected_result는 엔진과 일치 — 학습 라벨 SSOT는 유효. "
            "모델 실패는 데이터 라벨 문제가 아니라 추론·용량·커리큘럼 쪽."
        )
    elif gold_engine_ok < n:
        rec.append(
            "일부 골든·엔진 불일치 — golden JSONL 재생성(prep_myeongri_deterministic_lora_golden_v1) 검토."
        )
    if classes.get("model_mode_collapse_while_golden_ok", 0) > 0:
        rec.append(
            "mode collapse(계묘/신사 수렴) — TinyLlama 한계 가능; Qwen eval 후에도 지속 시 "
            "프롬프트에 birth_instant_utc 반복 강조·negative 예시 또는 더 큰 train_steps."
        )
    doc["recommendations_ko"] = rec

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "classification_counts": dict(classes)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
