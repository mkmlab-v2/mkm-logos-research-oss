#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build `myeongni_full_report_v1` from `saju_global_birth_result_v1` (stdin or --input-json)."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.manseryeok_perfect_final import PerfectManseryeok

SCHOOL_RESOLVER_PATH = ROOT / "data" / "myeongni" / "myeongni_school_conflict_resolver_v1.json"
RUNTIME_MODE_PATH = ROOT / "reports" / "myeongni_conflict_arbitration_runtime_mode_latest.json"
PRESET_AUDIT_LOG_PATH = ROOT / "reports" / "myeongni_conflict_arbitration_preset_apply_log.jsonl"
STAGE2_OVERRIDE_PATH = ROOT / "docs" / "final" / "artifacts" / "myeongni_stage2_threshold_override_latest.json"

STEM_ELEMENT = {
    "갑": "목(陽)",
    "을": "목(陰)",
    "병": "화(陽)",
    "정": "화(陰)",
    "무": "토(陽)",
    "기": "토(陰)",
    "경": "금(陽)",
    "신": "금(陰)",
    "임": "수(陽)",
    "계": "수(陰)",
}

ELEMENT_ONLY = {
    "갑": "목",
    "을": "목",
    "병": "화",
    "정": "화",
    "무": "토",
    "기": "토",
    "경": "금",
    "신": "금",
    "임": "수",
    "계": "수",
}

STEM_POLARITY = {
    "갑": "양",
    "을": "음",
    "병": "양",
    "정": "음",
    "무": "양",
    "기": "음",
    "경": "양",
    "신": "음",
    "임": "양",
    "계": "음",
}

BRANCH_MAIN_ELEMENT = {
    "자": "수",
    "축": "토",
    "인": "목",
    "묘": "목",
    "진": "토",
    "사": "화",
    "오": "화",
    "미": "토",
    "신": "금",
    "유": "금",
    "술": "토",
    "해": "수",
}

# Common hidden stems by branch for readable structured summaries.
BRANCH_HIDDEN_STEMS = {
    "자": ["계"],
    "축": ["기", "계", "신"],
    "인": ["갑", "병", "무"],
    "묘": ["을"],
    "진": ["무", "을", "계"],
    "사": ["병", "경", "무"],
    "오": ["정", "기"],
    "미": ["기", "을", "정"],
    "신": ["경", "임", "무"],
    "유": ["신"],
    "술": ["무", "신", "정"],
    "해": ["임", "갑"],
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_birth(path: Path | None, stdin: bool) -> dict[str, Any]:
    if stdin:
        return json.loads(sys.stdin.read())
    if path is None:
        raise SystemExit("need --input-json or stdin")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_json_if_exists(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _read_last_jsonl_row(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    for line in reversed(lines):
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _from_run_cli(local_y: int, local_mo: int, local_d: int, h: int, mi: int, s: int, iana: str, male: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_saju_global_birth_v1.py"),
        "--local",
        str(local_y),
        str(local_mo),
        str(local_d),
        str(h),
        str(mi),
        str(s),
        "--iana-tz",
        iana,
    ]
    if male:
        cmd.append("--is-male")
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout)
    return json.loads(cp.stdout)


def _ten_god(day_stem: str, target_stem: str) -> str:
    day_elem = ELEMENT_ONLY.get(day_stem)
    tar_elem = ELEMENT_ONLY.get(target_stem)
    if not day_elem or not tar_elem:
        return ""
    day_pol = STEM_POLARITY.get(day_stem)
    tar_pol = STEM_POLARITY.get(target_stem)
    same_pol = day_pol == tar_pol
    cycle_gen = {"목": "화", "화": "토", "토": "금", "금": "수", "수": "목"}
    cycle_ctrl = {"목": "토", "화": "금", "토": "수", "금": "목", "수": "화"}

    if day_elem == tar_elem:
        return "비견" if same_pol else "겁재"
    if cycle_gen[day_elem] == tar_elem:
        return "식신" if same_pol else "상관"
    if cycle_ctrl[day_elem] == tar_elem:
        return "편재" if same_pol else "정재"
    if cycle_gen[tar_elem] == day_elem:
        return "편인" if same_pol else "정인"
    if cycle_ctrl[tar_elem] == day_elem:
        return "편관" if same_pol else "정관"
    return ""


def _split_ganji(pillar: str | None) -> tuple[str, str]:
    if not pillar:
        return "", ""
    val = pillar.strip()
    if len(val) < 2:
        return "", ""
    return val[0], val[1]


def _element_profile(pillars: dict[str, str]) -> dict[str, Any]:
    elements = {"목": 0, "화": 0, "토": 0, "금": 0, "수": 0}
    stems: list[str] = []
    branches: list[str] = []
    hidden_stems: list[str] = []
    for k in ("year", "month", "day", "hour"):
        g, z = _split_ganji(pillars.get(k))
        if g:
            stems.append(g)
            elem = ELEMENT_ONLY.get(g)
            if elem:
                elements[elem] += 1
        if z:
            branches.append(z)
            be = BRANCH_MAIN_ELEMENT.get(z)
            if be:
                elements[be] += 1
            hidden_stems.extend(BRANCH_HIDDEN_STEMS.get(z, []))
    max_e = max(elements, key=elements.get) if elements else ""
    min_e = min(elements, key=elements.get) if elements else ""
    return {
        "element_counts_visible": elements,
        "dominant_element_visible": max_e,
        "weakest_element_visible": min_e,
        "stems": stems,
        "branches": branches,
        "hidden_stems_by_branch": hidden_stems,
    }


def _ten_god_profile(day_stem: str, stems: list[str], hidden_stems: list[str]) -> dict[str, Any]:
    tg_visible: list[dict[str, str]] = []
    tg_hidden: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for st in stems:
        tg = _ten_god(day_stem, st)
        tg_visible.append({"stem": st, "ten_god": tg})
        if tg:
            counts[tg] = counts.get(tg, 0) + 1
    for st in hidden_stems:
        tg = _ten_god(day_stem, st)
        tg_hidden.append({"stem": st, "ten_god": tg})
        if tg:
            counts[tg] = counts.get(tg, 0) + 1
    return {
        "visible_stem_ten_gods": tg_visible,
        "hidden_stem_ten_gods": tg_hidden,
        "ten_god_counts_combined": counts,
    }


def _strength_hint(month_branch: str, day_element: str, counts: dict[str, int]) -> dict[str, Any]:
    season_support = {
        "인": "목",
        "묘": "목",
        "진": "목",
        "사": "화",
        "오": "화",
        "미": "화",
        "신": "금",
        "유": "금",
        "술": "금",
        "해": "수",
        "자": "수",
        "축": "수",
    }
    season_elem = season_support.get(month_branch, "")
    dm_visible = counts.get(day_element, 0)
    season_bonus = 1 if season_elem == day_element else 0
    score = dm_visible + season_bonus
    if score >= 3:
        label = "강"
    elif score == 2:
        label = "중강"
    elif score == 1:
        label = "중약"
    else:
        label = "약"
    return {
        "month_branch": month_branch,
        "season_element_hint": season_elem,
        "day_master_element": day_element,
        "visible_count_day_element": dm_visible,
        "season_bonus": season_bonus,
        "strength_label": label,
        "note": "간이 추정(visible+월지 계절)이며, 용신 확정은 별도 전문 규칙이 필요",
    }


def _school_conflict_resolution(
    strength_label: str,
    ten_god_counts: dict[str, int],
    element_counts: dict[str, int],
) -> dict[str, Any]:
    policy = json.loads(SCHOOL_RESOLVER_PATH.read_text(encoding="utf-8-sig"))
    ws = policy.get("weights") or {}
    w_strength = float(ws.get("strength", 0.4))
    w_ten_god = float(ws.get("ten_god", 0.35))
    w_element = float(ws.get("element_balance", 0.25))

    strength_map = (policy.get("strength_school_score") or {}).get(strength_label) or {}
    strength_balance = float(strength_map.get("balance_centered", 0.5))
    strength_flow = float(strength_map.get("flow_centered", 0.5))

    tg_map = policy.get("ten_god_school_map") or {}
    tg_total = max(1, sum(int(v) for v in ten_god_counts.values()))
    tg_flow = 0.0
    for tg, cnt in ten_god_counts.items():
        if tg_map.get(tg) == "flow_centered":
            tg_flow += float(cnt)
    tg_flow /= tg_total
    tg_balance = 1.0 - tg_flow

    values = [float(element_counts.get(k, 0)) for k in ("목", "화", "토", "금", "수")]
    std = statistics.pstdev(values) if values else 0.0
    cut = policy.get("element_balance_cutoff") or {}
    balanced_std_max = float(cut.get("balanced_std_max", 0.75))
    unbalanced_std_min = float(cut.get("unbalanced_std_min", 1.05))
    if std <= balanced_std_max:
        elem_balance = 0.7
    elif std >= unbalanced_std_min:
        elem_balance = 0.3
    else:
        elem_balance = 0.5
    elem_flow = 1.0 - elem_balance

    score_balance = (w_strength * strength_balance) + (w_ten_god * tg_balance) + (w_element * elem_balance)
    score_flow = (w_strength * strength_flow) + (w_ten_god * tg_flow) + (w_element * elem_flow)
    decision = "balance_centered" if score_balance >= score_flow else "flow_centered"
    confidence = max(score_balance, score_flow)

    d = policy.get("decision") or {}
    min_conf = float(d.get("min_confidence", 0.55))
    if confidence < min_conf:
        decision = "hybrid_guarded"

    return {
        "schema": "myeongni_school_conflict_resolution_v1",
        "policy_schema": policy.get("schema"),
        "policy_version": policy.get("version"),
        "decision": decision,
        "confidence": round(confidence, 6),
        "scores": {
            "balance_centered": round(score_balance, 6),
            "flow_centered": round(score_flow, 6),
        },
        "inputs": {
            "strength_label": strength_label,
            "ten_god_counts_combined": ten_god_counts,
            "element_counts_visible": element_counts,
            "element_stddev_visible": round(std, 6),
        },
        "note": "MKM proprietary arbitration between balance-centered and flow-centered schools.",
    }


def _build_annual_fortune(
    birth_year: int,
    annual_start_year: int,
    annual_years: int,
    daewoon_cycles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    eng = PerfectManseryeok()
    out: list[dict[str, Any]] = []
    end_year = annual_start_year + max(0, annual_years)
    for y in range(annual_start_year, end_year):
        age = y - birth_year
        dw_match = None
        for c in daewoon_cycles:
            a0 = c.get("age_start")
            a1 = c.get("age_end")
            if isinstance(a0, (int, float)) and isinstance(a1, (int, float)) and a0 <= age < a1:
                dw_match = c
                break
        year_pillar = eng.calculate_year_pillar(y, 7, 1)
        g, z = _split_ganji(year_pillar)
        out.append(
            {
                "year": y,
                "age_kor_nominal": age + 1,
                "age_international": age,
                "sewoon_pillar": year_pillar,
                "sewoon_stem_ten_god": "",
                "daewoon_cycle": dw_match.get("cycle") if isinstance(dw_match, dict) else None,
                "daewoon_pillar": dw_match.get("pillar") if isinstance(dw_match, dict) else None,
                "sewoon_main_element": BRANCH_MAIN_ELEMENT.get(z, ""),
                "sewoon_note": "연운 간지는 해당 연도 중간일(7/1) 기준 보조값",
                "_stem": g,
            }
        )
    return out


def _build_monthly_fortune(
    annual_rows: list[dict[str, Any]],
    day_stem: str,
    months_per_year: int,
) -> list[dict[str, Any]]:
    if months_per_year <= 0:
        return []
    eng = PerfectManseryeok()
    rows: list[dict[str, Any]] = []
    for ar in annual_rows:
        year = int(ar.get("year"))
        for month in range(1, min(months_per_year, 12) + 1):
            month_pillar = eng.calculate_month_pillar(year, month, 15)
            mg, mz = _split_ganji(month_pillar)
            rows.append(
                {
                    "year": year,
                    "month": month,
                    "wolwoon_pillar": month_pillar,
                    "wolwoon_stem_ten_god": _ten_god(day_stem, mg),
                    "wolwoon_main_element": BRANCH_MAIN_ELEMENT.get(mz, ""),
                    "linked_sewoon_pillar": ar.get("sewoon_pillar"),
                    "linked_daewoon_pillar": ar.get("daewoon_pillar"),
                    "wolwoon_note": "월운 간지는 해당 월 중간일(15일) 기준 보조값",
                }
            )
    return rows


def _build_report(
    birth: dict[str, Any],
    annual_start_year: int,
    annual_years: int,
    months_per_year: int,
    runtime_mode_doc: dict[str, Any] | None = None,
    preset_audit_last: dict[str, Any] | None = None,
    stage2_override_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if birth.get("schema") != "saju_global_birth_result_v1":
        raise ValueError("expected saju_global_birth_result_v1")
    res = birth.get("resolution") or {}
    full = birth.get("full_saju") or {}
    pillars_raw = full.get("saju") if isinstance(full.get("saju"), dict) else {}
    ilgan = full.get("ilgan") or ""
    stem = ilgan[:1] if ilgan else ""
    year_gan, year_ji = _split_ganji(pillars_raw.get("year"))
    month_gan, month_ji = _split_ganji(pillars_raw.get("month"))
    day_gan, day_ji = _split_ganji(pillars_raw.get("day"))
    hour_gan, hour_ji = _split_ganji(pillars_raw.get("hour"))
    stem_list = [x for x in (year_gan, month_gan, day_gan, hour_gan) if x]
    elem_profile = _element_profile(pillars_raw)
    ten_god = _ten_god_profile(stem, stem_list, elem_profile["hidden_stems_by_branch"])
    strength = _strength_hint(month_ji, ELEMENT_ONLY.get(stem, ""), elem_profile["element_counts_visible"])
    school_resolution = _school_conflict_resolution(
        str(strength.get("strength_label") or ""),
        ten_god.get("ten_god_counts_combined") or {},
        elem_profile.get("element_counts_visible") or {},
    )
    dw_list = full.get("daewoon") or []
    cycles = []
    for row in dw_list:
        if not isinstance(row, dict):
            continue
        cycles.append(
            {
                "age_start": row.get("age_start"),
                "age_end": row.get("age_end"),
                "pillar": row.get("saju"),
                "cycle": row.get("cycle"),
            }
        )

    qiyun = full.get("daewoon_qiyun_v1") or {}
    direction = "backward" if qiyun.get("forward") is False else "forward"
    birth_info = full.get("birth_info") if isinstance(full.get("birth_info"), dict) else {}
    birth_year = int(birth_info.get("year") or res.get("engine_inputs", {}).get("year") or datetime.now().year)
    annual_rows = _build_annual_fortune(birth_year, annual_start_year, annual_years, cycles)
    for row in annual_rows:
        row["sewoon_stem_ten_god"] = _ten_god(stem, row.pop("_stem", ""))
    monthly_rows = _build_monthly_fortune(annual_rows, stem, months_per_year)
    runtime_mode_summary = None
    if runtime_mode_doc:
        runtime_mode_summary = {
            "schema": runtime_mode_doc.get("schema"),
            "generated_at_utc": runtime_mode_doc.get("generated_at_utc"),
            "mode": runtime_mode_doc.get("mode"),
            "policy_hash": runtime_mode_doc.get("policy_hash"),
            "verification_pass": runtime_mode_doc.get("verification_pass"),
            "actor": runtime_mode_doc.get("actor"),
        }
    preset_audit_summary = None
    if preset_audit_last:
        preset_audit_summary = {
            "schema": preset_audit_last.get("schema"),
            "ts_utc": preset_audit_last.get("ts_utc"),
            "preset": preset_audit_last.get("preset"),
            "old_hash": preset_audit_last.get("old_hash"),
            "new_hash": preset_audit_last.get("new_hash"),
            "verification_pass": preset_audit_last.get("verification_pass"),
            "reason": preset_audit_last.get("reason"),
            "actor": preset_audit_last.get("actor"),
        }
    stage2_summary = None
    if stage2_override_doc:
        stage2_summary = {
            "schema": stage2_override_doc.get("schema"),
            "applied_at_utc": stage2_override_doc.get("applied_at_utc"),
            "track": stage2_override_doc.get("track"),
            "profile_baseline": stage2_override_doc.get("profile_baseline"),
            "thresholds": stage2_override_doc.get("thresholds"),
            "source_calibration_json": stage2_override_doc.get("source_calibration_json"),
        }

    return {
        "schema": "myeongni_full_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _now_utc(),
        "birth_engine": {
            "resolution": res,
            "calculation_method": full.get("calculation_method"),
            "calculated_at": full.get("calculated_at"),
            "note": full.get("note"),
            "verification": full.get("verification"),
        },
        "pillars": {
            "year": pillars_raw.get("year"),
            "month": pillars_raw.get("month"),
            "day": pillars_raw.get("day"),
            "hour": pillars_raw.get("hour"),
        },
        "day_master": {
            "stem_hangul": ilgan,
            "stem_element_hint": STEM_ELEMENT.get(stem, ""),
        },
        "structure_analysis": {
            "pillars_split": {
                "year": {"stem": year_gan, "branch": year_ji},
                "month": {"stem": month_gan, "branch": month_ji},
                "day": {"stem": day_gan, "branch": day_ji},
                "hour": {"stem": hour_gan, "branch": hour_ji},
            },
            "element_profile": elem_profile,
            "ten_god_profile": ten_god,
            "day_master_strength_hint": strength,
            "school_conflict_resolution_v1": school_resolution,
        },
        "daewoon": {
            "direction": direction,
            "qiyun": qiyun,
            "cycles": cycles,
        },
        "annual_fortune": {
            "start_year": annual_start_year,
            "years": annual_years,
            "rows": annual_rows,
        },
        "monthly_fortune": {
            "months_per_year": months_per_year,
            "rows": monthly_rows,
        },
        "engine_metadata": {
            "birth_info": birth_info,
            "note": full.get("note"),
        },
        "runtime_governance": {
            "conflict_arbitration_runtime_mode": runtime_mode_summary,
            "conflict_arbitration_last_preset_audit": preset_audit_summary,
            "stage2_threshold_override": stage2_summary,
            "references": {
                "runtime_mode_path": str(RUNTIME_MODE_PATH),
                "preset_apply_log_path": str(PRESET_AUDIT_LOG_PATH),
                "stage2_threshold_override_path": str(STAGE2_OVERRIDE_PATH),
            },
        },
        "disclaimers": [
            "본 리포트의 사주 간지·대운 표는 로컬 엔진(saju_global_birth_result_v1) 산출을 그대로 옮긴 것이며, 의료·법률·투자 행위의 근거가 될 수 없다.",
            "해석 문단은 전통 명리의 상징적 프레임일 뿐, 검증된 예측 정확도를 주장하지 않는다.",
            "PerfectManseryeok의 표준 DB 미사용·fallback 경로일 경우 verification.reason을 확인한다.",
        ],
    }


def _markdown(r: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MKM 명리 풀 리포트 (엔진 근거)")
    lines.append("")
    lines.append(f"- 스키마: `{r['schema']}` `{r['version']}`")
    lines.append(f"- 생성(UTC): `{r['generated_at_utc']}`")
    lines.append("")
    lines.append("## 1. 출생 입력·해석 (Fact)")
    be = r.get("birth_engine") or {}
    res = be.get("resolution") or {}
    lines.append(f"- birth_instant_utc: `{res.get('birth_instant_utc')}`")
    lines.append(f"- iana_tz: `{res.get('iana_tz')}`")
    lines.append(f"- local_iso: `{res.get('local_iso')}`")
    ei = res.get("engine_inputs") or {}
    lines.append(
        f"- engine_inputs (y/m/d/h): `{ei.get('year')}/{ei.get('month')}/{ei.get('day')}` hour={ei.get('hour')}"
    )
    warns = res.get("warnings") or []
    if warns:
        lines.append(f"- warnings: {warns}")
    lines.append(f"- calculation_method: `{be.get('calculation_method')}`")
    ver = be.get("verification") or {}
    if ver:
        lines.append(f"- verification: `{ver}`")
    lines.append("")
    lines.append("## 2. 사주 원국 (네 기둥)")
    p = r.get("pillars") or {}
    lines.append(f"| 구분 | 간지 |")
    lines.append("| --- | --- |")
    lines.append(f"| 연주 | {p.get('year')} |")
    lines.append(f"| 월주 | {p.get('month')} |")
    lines.append(f"| 일주 | {p.get('day')} |")
    lines.append(f"| 시주 | {p.get('hour')} |")
    dm = r.get("day_master") or {}
    lines.append("")
    lines.append(f"- 일간(日干): **{dm.get('stem_hangul')}** ({dm.get('stem_element_hint')})")
    lines.append("")
    lines.append("## 3. 구조 프로파일 (오행·십성·강약 힌트)")
    sa = r.get("structure_analysis") or {}
    ep = sa.get("element_profile") or {}
    ec = ep.get("element_counts_visible") or {}
    lines.append(f"- 오행 가시 카운트(천간+지지 본기): 목={ec.get('목',0)} 화={ec.get('화',0)} 토={ec.get('토',0)} 금={ec.get('금',0)} 수={ec.get('수',0)}")
    lines.append(f"- 우세/약세(가시): `{ep.get('dominant_element_visible')}` / `{ep.get('weakest_element_visible')}`")
    tg = sa.get("ten_god_profile") or {}
    tgc = tg.get("ten_god_counts_combined") or {}
    if tgc:
        top_tg = sorted(tgc.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append(f"- 십성 다빈도(천간+지장간): {top_tg}")
    sh = sa.get("day_master_strength_hint") or {}
    if sh:
        lines.append(
            f"- 일간 강약 힌트: `{sh.get('strength_label')}` (월지={sh.get('month_branch')}, 계절={sh.get('season_element_hint')}, 일간오행={sh.get('day_master_element')})"
        )
        lines.append(f"- 강약 산정 메모: {sh.get('note')}")
    lines.append("")
    lines.append("## 4. 대운 (엔진 순서 그대로)")
    dw = r.get("daewoon") or {}
    lines.append(f"- 방향: `{dw.get('direction')}` (엔진 메타 `forward` 반대 여부 기준)")
    q = dw.get("qiyun") or {}
    if q:
        lines.append(f"- 기운(qiyun): years≈`{q.get('qiyun_years_float')}`, days≈`{q.get('qiyun_days')}`, method=`{q.get('method')}`")
    lines.append("")
    lines.append("| 연령(세) | 대운 간지 | cycle |")
    lines.append("| --- | --- | --- |")
    for c in dw.get("cycles") or []:
        a0 = c.get("age_start")
        a1 = c.get("age_end")
        lines.append(f"| {a0}–{a1} | {c.get('pillar')} | {c.get('cycle')} |")
    lines.append("")
    lines.append("## 5. 세운 (연도별)")
    af = r.get("annual_fortune") or {}
    lines.append(f"- 범위: `{af.get('start_year')}..{(af.get('start_year') or 0) + (af.get('years') or 0) - 1}`")
    lines.append("| 연도 | 나이(만) | 나이(한국식) | 세운 | 세운십성(천간) | 동시 대운 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in af.get("rows") or []:
        lines.append(
            f"| {row.get('year')} | {row.get('age_international')} | {row.get('age_kor_nominal')} | "
            f"{row.get('sewoon_pillar')} | {row.get('sewoon_stem_ten_god')} | {row.get('daewoon_pillar')} |"
        )
    lines.append("")
    lines.append("## 6. 월운 (연도별 월분해)")
    mf = r.get("monthly_fortune") or {}
    mpy = int(mf.get("months_per_year") or 0)
    lines.append(f"- months_per_year: `{mpy}`")
    lines.append("| 연도-월 | 월운 | 월운십성(천간) | 동시 세운 | 동시 대운 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in mf.get("rows") or []:
        ym = f"{row.get('year')}-{int(row.get('month')):02d}"
        lines.append(
            f"| {ym} | {row.get('wolwoon_pillar')} | {row.get('wolwoon_stem_ten_god')} | "
            f"{row.get('linked_sewoon_pillar')} | {row.get('linked_daewoon_pillar')} |"
        )
    lines.append("")
    lines.append("## 7. 구조적 해석 요약 (비단정·상징)")
    lines.append("- 일간이 금(庚)이면 단단한 원칙·경계를 중시하는 프레임으로 자주 읽힌다.")
    lines.append("- 월·시에 목(甲·寅)이 함께 있으면 대외적 실행·책임·추진의 무게가 커지기 쉽다.")
    lines.append("- 일지 진(辰)·시 무(戊)는 토 기운으로 현실적 누적·관리·버팀을 보조하는 축으로 묶인다.")
    lines.append("")
    lines.append("## 8. 면책")
    for d in r.get("disclaimers") or []:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## 9. 런타임 거버넌스")
    gov = r.get("runtime_governance") or {}
    mode = gov.get("conflict_arbitration_runtime_mode") or {}
    if mode:
        lines.append(
            f"- conflict_arbitration mode=`{mode.get('mode')}` hash=`{mode.get('policy_hash')}` verify_pass=`{mode.get('verification_pass')}`"
        )
    audit = gov.get("conflict_arbitration_last_preset_audit") or {}
    if audit:
        lines.append(
            f"- last_preset_audit ts=`{audit.get('ts_utc')}` preset=`{audit.get('preset')}` reason=`{audit.get('reason')}`"
        )
    s2 = gov.get("stage2_threshold_override") or {}
    if s2:
        th = s2.get("thresholds") or {}
        lines.append(
            "- stage2_override "
            f"hold={th.get('hold_confidence_cut')} reduce_dir={th.get('reduce_direction_cut')} reduce_conf={th.get('reduce_confidence_cut')}"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build myeongni_full_report_v1")
    ap.add_argument("--input-json", type=Path, help="Path to saju_global_birth_result_v1 JSON")
    ap.add_argument(
        "--local",
        nargs=6,
        type=int,
        metavar=("Y", "M", "D", "h", "m", "s"),
        help="Shortcut: run birth CLI then report",
    )
    ap.add_argument("--iana-tz", default="Asia/Seoul")
    ap.add_argument("--is-male", action="store_true")
    ap.add_argument("--annual-start-year", type=int, default=datetime.now().year, help="Annual fortune start year")
    ap.add_argument("--annual-years", type=int, default=5, help="Number of annual rows")
    ap.add_argument("--monthly-months-per-year", type=int, default=3, help="How many months per year to include (1-12)")
    ap.add_argument("--markdown", action="store_true", help="Print markdown to stdout after JSON")
    ap.add_argument("--out-json", type=Path, help="Write report JSON")
    ap.add_argument("--runtime-mode-json", type=Path, default=RUNTIME_MODE_PATH)
    ap.add_argument("--preset-apply-log-jsonl", type=Path, default=PRESET_AUDIT_LOG_PATH)
    ap.add_argument("--stage2-override-json", type=Path, default=STAGE2_OVERRIDE_PATH)
    args = ap.parse_args()

    if args.local:
        birth = _from_run_cli(
            args.local[0],
            args.local[1],
            args.local[2],
            args.local[3],
            args.local[4],
            args.local[5],
            args.iana_tz,
            args.is_male,
        )
    elif args.input_json:
        birth = _load_birth(args.input_json, stdin=False)
    else:
        birth = _load_birth(None, stdin=True)

    runtime_mode_doc = _read_json_if_exists(args.runtime_mode_json)
    preset_audit_last = _read_last_jsonl_row(args.preset_apply_log_jsonl)
    stage2_override_doc = _read_json_if_exists(args.stage2_override_json)
    report = _build_report(
        birth,
        args.annual_start_year,
        args.annual_years,
        max(0, min(12, args.monthly_months_per_year)),
        runtime_mode_doc=runtime_mode_doc,
        preset_audit_last=preset_audit_last,
        stage2_override_doc=stage2_override_doc,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text, encoding="utf-8")
    print(text)
    if args.markdown:
        print()
        print("---")
        print()
        print(_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
