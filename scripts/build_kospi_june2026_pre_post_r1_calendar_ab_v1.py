#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre vs post R1 lens refresh June calendar A/B + neutral-20 decomposition [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar  # noqa: E402
from scripts.build_kospi_june2026_channel_input_audit_v1 import _neutral_vote_anatomy  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome, eval_calendar  # noqa: E402

MYEONGNI_STUB = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
SASANG_STUB = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
MYEONGNI_SESSION = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
SASANG_SESSION = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
PRE_LENS_DIR = ROOT / "reports/pre_r1_lens_shadow"
POST_LENS_DIR = ROOT / "reports/post_r1_lens_shadow"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_pre_post_r1_calendar_ab_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, *args: str) -> int:
    proc = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return int(proc.returncode)


def _direction_counts(cal: dict[str, Any]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for row in cal.get("rows") or []:
        c[str(row.get("predicted_direction") or "neutral")] += 1
    return dict(c)


def _neutral_root_cause(row: dict[str, Any]) -> str:
    if str(row.get("predicted_direction") or "") != "neutral":
        return "not_neutral"
    anatomy = _neutral_vote_anatomy(row)
    session_map = str(row.get("session_mapping_target") or "sideways")
    resolution = str(anatomy.get("winner_resolution") or "")
    if session_map == "sideways":
        return "session_sideways_dominant"
    if resolution == "neutral_plurality":
        return "neutral_plurality"
    gap = float(anatomy.get("gap_directional_minus_neutral") or 0)
    if gap < 0.05:
        return "directional_votes_too_weak"
    blend = row.get("blend") if isinstance(row.get("blend"), dict) else {}
    channels = blend.get("channels") if isinstance(blend.get("channels"), list) else []
    neutral_weight = sum(
        float(ch.get("weight") or 0)
        for ch in channels
        if str(ch.get("direction") or "") == "neutral"
    )
    if neutral_weight >= 0.7:
        return "heavy_neutral_channel_weights"
    return "other_neutral"


def _decompose_neutral(cal: dict[str, Any], *, label: str) -> dict[str, Any]:
    neutral_rows = [r for r in cal.get("rows") or [] if str(r.get("predicted_direction") or "") == "neutral"]
    causes: Counter[str] = Counter()
    for row in neutral_rows:
        causes[_neutral_root_cause(row)] += 1
    return {
        "label": label,
        "n_neutral": len(neutral_rows),
        "root_cause_counts": dict(causes),
        "sample_days": [
            {
                "session_date": r.get("session_date"),
                "session_mapping_target": r.get("session_mapping_target"),
                "root_cause": _neutral_root_cause(r),
                "votes": (r.get("blend") or {}).get("votes"),
            }
            for r in neutral_rows[:8]
        ],
    }


def _lens_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"missing": True}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ds = scores.get("direction_score")
    direction = "neutral"
    if ds is not None:
        ds_f = float(ds)
        direction = "bull" if ds_f > 0.05 else "bear" if ds_f < -0.05 else "neutral"
    return {
        "direction": direction,
        "direction_score": ds,
        "row_ts_utc": prov.get("row_ts_utc"),
        "input_path": prov.get("input_path"),
    }


def build_ab(*, year_month: str, as_of_kst: str) -> dict[str, Any]:
    PRE_LENS_DIR.mkdir(parents=True, exist_ok=True)
    POST_LENS_DIR.mkdir(parents=True, exist_ok=True)
    pre_myeongni = PRE_LENS_DIR / "myeongni_independent_lens_pre_r1.json"
    pre_sasang = PRE_LENS_DIR / "sasang_independent_lens_pre_r1.json"
    post_myeongni = POST_LENS_DIR / "myeongni_independent_lens_post_r1.json"
    post_sasang = POST_LENS_DIR / "sasang_independent_lens_post_r1.json"

    steps: list[dict[str, Any]] = []
    rc = _run_py(
        "scripts/run_lens_myeongni.py",
        "--experiment-jsonl",
        str(MYEONGNI_STUB),
        "--output",
        str(pre_myeongni),
    )
    steps.append({"step": "pre_myeongni_lens", "exit_code": rc})
    rc = _run_py("scripts/run_lens_sasang.py", "--input-jsonl", str(SASANG_STUB), "--output", str(pre_sasang))
    steps.append({"step": "pre_sasang_lens", "exit_code": rc})
    rc = _run_py(
        "scripts/run_lens_myeongni.py",
        "--experiment-jsonl",
        str(MYEONGNI_SESSION),
        "--output",
        str(post_myeongni),
    )
    steps.append({"step": "post_myeongni_lens", "exit_code": rc})
    rc = _run_py(
        "scripts/run_lens_sasang.py",
        "--input-jsonl",
        str(SASANG_SESSION),
        "--output",
        str(post_sasang),
    )
    steps.append({"step": "post_sasang_lens", "exit_code": rc})

    pre_cal = build_calendar(
        year_month=year_month,
        skip_panel=True,
        profile="v2_multilens",
        myeongni_lens_json=pre_myeongni,
        sasang_lens_json=pre_sasang,
    )
    post_cal = build_calendar(
        year_month=year_month,
        skip_panel=True,
        profile="v2_multilens",
        myeongni_lens_json=post_myeongni,
        sasang_lens_json=post_sasang,
    )

    pre_counts = _direction_counts(pre_cal)
    post_counts = _direction_counts(post_cal)
    diffs: list[dict[str, Any]] = []
    pre_by = {str(r["session_date"]): r for r in pre_cal.get("rows") or []}
    post_by = {str(r["session_date"]): r for r in post_cal.get("rows") or []}
    for dk in sorted(set(pre_by) & set(post_by)):
        p_dir = str(pre_by[dk].get("predicted_direction") or "")
        q_dir = str(post_by[dk].get("predicted_direction") or "")
        if p_dir != q_dir:
            diffs.append(
                {
                    "session_date": dk,
                    "pre_r1": p_dir,
                    "post_r1": q_dir,
                    "pre_session_map": pre_by[dk].get("session_mapping_target"),
                    "post_session_map": post_by[dk].get("session_mapping_target"),
                }
            )

    pre_eval = eval_calendar(pre_cal, as_of_kst=as_of_kst)
    post_eval = eval_calendar(post_cal, as_of_kst=as_of_kst)

    pre_neutral_decomp = _decompose_neutral(pre_cal, label="pre_r1")
    post_neutral_decomp = _decompose_neutral(post_cal, label="post_r1")

    # Channel flip attribution on diff days
    flip_attribution: list[dict[str, Any]] = []
    for d in diffs[:21]:
        dk = d["session_date"]
        pre_ch = (pre_by[dk].get("blend") or {}).get("channels") or []
        post_ch = (post_by[dk].get("blend") or {}).get("channels") or []
        pre_map = {str(c.get("channel")): c for c in pre_ch if isinstance(c, dict)}
        post_map = {str(c.get("channel")): c for c in post_ch if isinstance(c, dict)}
        changed = []
        for ch in ("myeongni_independent", "sasang", "macro", "session_myeongni"):
            if pre_map.get(ch, {}).get("direction") != post_map.get(ch, {}).get("direction"):
                changed.append(
                    {
                        "channel": ch,
                        "pre": pre_map.get(ch, {}).get("direction"),
                        "post": post_map.get(ch, {}).get("direction"),
                    }
                )
        flip_attribution.append({"session_date": dk, "pre_to_post": f"{d['pre_r1']}→{d['post_r1']}", "channel_flips": changed})

    return {
        "schema": "kospi_june2026_pre_post_r1_calendar_ab_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "lens_inputs": {
            "pre_r1": {"myeongni_jsonl": str(MYEONGNI_STUB), "sasang_jsonl": str(SASANG_STUB)},
            "post_r1": {"myeongni_jsonl": str(MYEONGNI_SESSION), "sasang_jsonl": str(SASANG_SESSION)},
        },
        "lens_snapshots": {
            "pre_r1": {"myeongni": _lens_snapshot(pre_myeongni), "sasang": _lens_snapshot(pre_sasang)},
            "post_r1": {"myeongni": _lens_snapshot(post_myeongni), "sasang": _lens_snapshot(post_sasang)},
        },
        "direction_counts": {"pre_r1": pre_counts, "post_r1": post_counts},
        "n_direction_diffs": len(diffs),
        "direction_diff_sample": diffs[:15],
        "forward_eval": {
            "pre_r1": {"n_scored": pre_eval.get("n_scored"), "metrics": pre_eval.get("metrics")},
            "post_r1": {"n_scored": post_eval.get("n_scored"), "metrics": post_eval.get("metrics")},
            "soft_delta_post_minus_pre": round(
                float((post_eval.get("metrics") or {}).get("soft_hit_rate") or 0)
                - float((pre_eval.get("metrics") or {}).get("soft_hit_rate") or 0),
                4,
            )
            if pre_eval.get("n_scored") and post_eval.get("n_scored")
            else None,
        },
        "neutral_decomposition": {
            "pre_r1_replay": pre_neutral_decomp,
            "post_r1": post_neutral_decomp,
        },
        "flip_attribution": flip_attribution[:12],
        "steps": steps,
        "verdict_ko": (
            "R1 렌즈 tail 갱신이 sasang/myeongni static 입력을 바꿔 캘린더 bull→neutral drift — "
            "apply 없음; published 캘린더는 --output-only shadow 빌드 권장."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--as-of-kst", default="2026-06-05")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    doc = build_ab(year_month=args.year_month, as_of_kst=args.as_of_kst)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} "
        f"pre={doc['direction_counts']['pre_r1']} post={doc['direction_counts']['post_r1']} "
        f"diffs={doc['n_direction_diffs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
