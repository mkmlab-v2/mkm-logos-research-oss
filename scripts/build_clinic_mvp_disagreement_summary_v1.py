"""
Aggregate clinic constitution MVP JSONL → disagreement summary (B-track, research_only).

Reads data/clinic/clinic_constitution_mvp_v1*.jsonl (validated lines only).
Does not promote Track A, trading, or clinical diagnosis claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.clinic_constitution_mvp_ledger_v1 import (
    LEDGER_PREFIX,
    WORKSPACE_DATA_REL,
    validate_clinic_capture_record,
    validate_jsonl_file,
)

SUMMARY_SCHEMA = "clinic_mvp_disagreement_summary_v1"
SUMMARY_VERSION = "1.0.0"
FOUR_LABELS = frozenset({"taeeum", "soyang", "taeyang", "soeum"})
NON_COMPARABLE_PHYSICIAN = frozenset({"uncertain", "withheld"})


def _workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_ts(ts: str) -> datetime | None:
    if not isinstance(ts, str) or not ts.strip():
        return None
    s = ts.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _labels_comparable(ai_label: str, physician_label: str) -> bool:
    return ai_label in FOUR_LABELS and physician_label in FOUR_LABELS


def _label_match(ai_label: str, physician_label: str) -> bool:
    return ai_label == physician_label


def _infer_disagreement_code(
    *,
    match: bool,
    ai_conf: float,
    physician_label: str,
    recorded_code: str | None,
) -> str:
    if recorded_code and recorded_code != "none":
        return recorded_code
    if match:
        return "none"
    if physician_label in NON_COMPARABLE_PHYSICIAN:
        return "physician_withheld"
    if ai_conf >= 0.55:
        return "ai_overconfident"
    if ai_conf < 0.45:
        return "ai_underconfident"
    return "modality_insufficient"


def _load_records(paths: list[Path]) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{path.name}:{i} json: {e}")
                continue
            errs = validate_clinic_capture_record(obj)
            if errs:
                errors.append(f"{path.name}:{i} validate: {'; '.join(errs)}")
                continue
            records.append(obj)
    return records, errors


def build_disagreement_summary(
    records: list[dict[str, Any]],
    *,
    ledger_files: list[str],
    parse_errors: list[str],
    since_utc: datetime | None = None,
) -> dict[str, Any]:
    if since_utc is not None:
        filtered: list[dict[str, Any]] = []
        for r in records:
            ts = _parse_ts(str(r.get("ts_utc", "")))
            if ts is None or ts >= since_utc:
                filtered.append(r)
        records = filtered

    n_total = len(records)
    disagreement_codes: Counter[str] = Counter()
    ai_labels: Counter[str] = Counter()
    physician_labels: Counter[str] = Counter()
    modality_face = modality_voice = modality_survey = 0
    n_comparable = 0
    n_match = 0
    conf_sum_match = 0.0
    conf_sum_mismatch = 0.0
    n_conf_match = 0
    n_conf_mismatch = 0
    by_lane: dict[str, dict[str, int]] = {}

    for r in records:
        lane = str(r.get("label_lane") or "physician_gold")
        lane_bucket = by_lane.setdefault(
            lane,
            {
                "n_lines": 0,
                "n_comparable_four_label": 0,
                "n_ai_physician_match": 0,
            },
        )
        lane_bucket["n_lines"] += 1
        ai = r["ai_hypothesis"]
        pc = r["physician_constitution"]
        ai_label = str(ai["constitution"])
        physician_label = str(pc["label"])
        ai_conf = float(ai["confidence"])
        ai_labels[ai_label] += 1
        physician_labels[physician_label] += 1

        mod = r.get("modalities_present") or {}
        if isinstance(mod, dict):
            if mod.get("face_image"):
                modality_face += 1
            if mod.get("voice_sample"):
                modality_voice += 1
            if mod.get("survey"):
                modality_survey += 1

        agr = r.get("agreement") if isinstance(r.get("agreement"), dict) else {}
        recorded_match = agr.get("ai_physician_match")
        recorded_code = agr.get("disagreement_code")

        comparable = _labels_comparable(ai_label, physician_label)
        if comparable:
            n_comparable += 1
            lane_bucket["n_comparable_four_label"] += 1
            match = _label_match(ai_label, physician_label)
            if recorded_match is not None and bool(recorded_match) != match:
                pass  # physician-entered agreement wins for code; match from labels for rate
            if match:
                n_match += 1
                lane_bucket["n_ai_physician_match"] += 1
                conf_sum_match += ai_conf
                n_conf_match += 1
            else:
                conf_sum_mismatch += ai_conf
                n_conf_mismatch += 1
            code = _infer_disagreement_code(
                match=match,
                ai_conf=ai_conf,
                physician_label=physician_label,
                recorded_code=str(recorded_code) if recorded_code else None,
            )
            disagreement_codes[code] += 1
        else:
            code = _infer_disagreement_code(
                match=False,
                ai_conf=ai_conf,
                physician_label=physician_label,
                recorded_code=str(recorded_code) if recorded_code else None,
            )
            disagreement_codes[code] += 1

    disagreement_rate = (
        round((n_comparable - n_match) / n_comparable, 4) if n_comparable else None
    )
    match_rate = round(n_match / n_comparable, 4) if n_comparable else None

    by_lane_out: dict[str, Any] = {}
    for lane, bucket in sorted(by_lane.items()):
        nc = bucket["n_comparable_four_label"]
        nm = bucket["n_ai_physician_match"]
        by_lane_out[lane] = {
            **bucket,
            "match_rate": round(nm / nc, 4) if nc else None,
            "disagreement_rate": round((nc - nm) / nc, 4) if nc else None,
        }

    return {
        "schema": SUMMARY_SCHEMA,
        "version": SUMMARY_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "hypothesis_tier": "B",
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "ledger_files": ledger_files,
        "n_lines_valid": n_total,
        "n_parse_or_validate_errors": len(parse_errors),
        "parse_errors_sample": parse_errors[:20],
        "n_comparable_four_label": n_comparable,
        "n_ai_physician_match": n_match,
        "match_rate": match_rate,
        "disagreement_rate": disagreement_rate,
        "disagreement_code_counts": dict(sorted(disagreement_codes.items())),
        "ai_constitution_counts": dict(sorted(ai_labels.items())),
        "physician_label_counts": dict(sorted(physician_labels.items())),
        "confidence_on_match_mean": round(conf_sum_match / n_conf_match, 4)
        if n_conf_match
        else None,
        "confidence_on_mismatch_mean": round(conf_sum_mismatch / n_conf_mismatch, 4)
        if n_conf_mismatch
        else None,
        "modality_present_counts": {
            "survey": modality_survey,
            "face_image": modality_face,
            "voice_sample": modality_voice,
        },
        "by_label_lane": by_lane_out,
        "dual_lane_policy_ref": "docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
        "guards": {
            "not_clinical_diagnosis": True,
            "not_for_track_a_promotion": True,
            "disagreement_rate_denominator": "four_label_ai_and_physician_only",
            "correlation_not_causation": True,
        },
        "operator_hint": (
            "낮은 n_comparable이면 불일치율 해석 금지. "
            "uncertain/withheld는 rate 분모에서 제외. "
            "consumer_survey_only 행은 physician KPI에 합산하지 말 것 — by_label_lane 참고."
        ),
    }


def _discover_jsonl(clinic_dir: Path) -> list[Path]:
    return sorted(clinic_dir.glob(f"{LEDGER_PREFIX}*.jsonl"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clinic MVP disagreement summary v1")
    p.add_argument(
        "--clinic-dir",
        type=Path,
        default=None,
        help="Directory with clinic_constitution_mvp_v1*.jsonl (default: data/clinic)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON (default: reports/clinic_mvp_disagreement_summary_latest.json)",
    )
    p.add_argument(
        "--since-days",
        type=int,
        default=None,
        help="Only include rows with ts_utc within last N days (UTC).",
    )
    p.add_argument(
        "--jsonl",
        type=Path,
        action="append",
        default=[],
        help="Explicit JSONL file(s); if omitted, glob clinic-dir.",
    )
    args = p.parse_args(argv)
    root = _workspace_root()
    clinic_dir = args.clinic_dir or (root / WORKSPACE_DATA_REL)
    paths = list(args.jsonl) if args.jsonl else _discover_jsonl(clinic_dir)
    if not paths:
        print(f"no ledger files under {clinic_dir}", file=__import__("sys").stderr)
        return 1

    since: datetime | None = None
    if args.since_days is not None:
        if args.since_days < 1:
            print("--since-days must be >= 1", file=__import__("sys").stderr)
            return 1
        since = datetime.now(timezone.utc) - timedelta(days=args.since_days)

    records, parse_errors = _load_records(paths)
    summary = build_disagreement_summary(
        records,
        ledger_files=[
            str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in paths
        ],
        parse_errors=parse_errors,
        since_utc=since,
    )
    out = args.out or (root / "reports/clinic_mvp_disagreement_summary_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: n_valid={summary['n_lines_valid']} comparable={summary['n_comparable_four_label']} "
        f"match_rate={summary['match_rate']} -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
