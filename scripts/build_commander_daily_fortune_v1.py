#!/usr/bin/env python3
"""Build commander personal daily fortune (Myeongni engine + MKM 4AI readout) for Telegram digest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
DEFAULT_PROFILE = ROOT / "docs" / "final" / "artifacts" / "commander_profile_v1.example.json"
DEFAULT_OUT = ROOT / "reports" / "commander_daily_fortune_latest.json"
DEFAULT_MISSION_LOG = ROOT / "MISSION_LOG.md"

# 4AI 축 ↔ 오행 부담 힌트 (교육용 [HYPO])
FOUR_AI_AXES = ("태양", "소양", "태음", "소음")
OHANG_TO_AI_WEIGHT = {
    "화": {"태양": 2, "소양": 1, "태음": 0, "소음": 0},
    "목": {"태양": 0, "소양": 2, "태음": 0, "소음": 1},
    "토": {"태양": 0, "소양": 0, "태음": 2, "소음": 1},
    "금": {"태양": 1, "소양": 0, "태음": 1, "소음": 1},
    "수": {"태양": 0, "소양": 1, "태음": 0, "소음": 2},
}

# MKM 4AI core ↔ 사상 체질 참조 (교육용 [HYPO]; 임상·실매매 합선 금지)
SASANG_4AI: Dict[str, Dict[str, Any]] = {
    "태양인": {
        "primary_ai": "태양",
        "lead": "결단·속도·외향 확장 — 다만 과열 시 소음(휴식) 보조",
        "balance_hint": "Absolute Balance: 소음 AI로 회복·페이싱 루틴을 먼저 잡을 때 품질 상승",
    },
    "소양인": {
        "primary_ai": "소양",
        "lead": "교류·유연·표현 — 과확장 시 태음(구조) 보조",
        "balance_hint": "Balance: 태음 AI로 일정·경계를 고정하면 산만함 감소",
    },
    "태음인": {
        "primary_ai": "태음",
        "lead": "구조·축적·보수 — 과잉 경직 시 소양(개방) 보조",
        "balance_hint": "Balance: 소양 AI로 가벼운 교류를 넣으면 답답함 완화",
    },
    "소음인": {
        "primary_ai": "소음",
        "lead": "휴식·내면·정밀 — 과잉 수축 시 태양(결단) 보조",
        "balance_hint": "Balance: 태양 AI로 한 가지 결단만 명확히 하면 정체 감소",
    },
}

TEN_GOD_HINTS: Dict[str, str] = {
    "비견": "자기 주장·경쟁 에너지",
    "겁재": "변동·분산 주의",
    "식신": "창작·완화·소화",
    "상관": "표현·개혁·말·결정 과부하 주의",
    "편재": "기회·이동·외부 자극",
    "정재": "안정 수입·루틴 정리",
    "편관": "압박·책임·규율",
    "정관": "질서·평가·공적 역할",
    "편인": "학습·직관·내면",
    "정인": "지원·회복·보호",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy_env(name: str, *, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _append_lifestyle_lines(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    telegram_lines: List[str],
) -> Dict[str, Any]:
    if not _truthy_env("MKM_LIFESTYLE_CONCIERGE_ENABLED", default=True):
        return {}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from commander_lifestyle_concierge_v1 import build_from_profile_report  # noqa: WPS433

        lifestyle = build_from_profile_report(profile, report, skip_weather_fetch=False)
        for ln in lifestyle.get("telegram_append_lines") or []:
            if ln:
                telegram_lines.append(ln)
        return lifestyle
    except Exception as exc:  # noqa: BLE001 — digest must not fail on lifestyle
        telegram_lines.extend(
            [
                "",
                "▸ 오늘 라이프 [가설]",
                f"  (생략: lifestyle 빌드 오류 {str(exc)[:80]})",
            ]
        )
        return {"status": "error", "error": str(exc)[:200]}


def _append_logos_anchor_lines(
    profile: Dict[str, Any],
    report: Dict[str, Any],
    lifestyle: Dict[str, Any],
    myeongni_lines: List[str],
    telegram_lines: List[str],
) -> Dict[str, Any]:
    if not _truthy_env("MKM_COMMANDER_LOGOS_ANCHOR_ENABLED", default=True):
        return {}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from commander_daily_logos_anchor_v1 import build_logos_anchor  # noqa: WPS433

        headline = ""
        for ln in myeongni_lines:
            if "오늘 한 줄" in ln:
                headline = ln
                break
        anchor = build_logos_anchor(
            profile,
            report,
            lifestyle=lifestyle or None,
            myeongni_headline_ko=headline,
        )
        for ln in anchor.get("telegram_append_lines") or []:
            if ln:
                telegram_lines.append(ln)
        return anchor
    except Exception as exc:  # noqa: BLE001
        telegram_lines.extend(
            [
                "",
                "▸ 성경 앵커 (Logos) [NON_GATING][가설]",
                f"  (생략: logos 앵커 오류 {str(exc)[:80]})",
            ]
        )
        return {"status": "error", "error": str(exc)[:200]}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _profile_path(cli: Optional[Path]) -> Path:
    if cli is not None:
        return cli
    env = os.getenv("MKM_COMMANDER_PROFILE_JSON", "").strip()
    if env:
        return Path(env)
    return DEFAULT_PROFILE


def _local_from_profile(profile: Dict[str, Any]) -> tuple[List[int], str, bool]:
    anchor = profile.get("birth_anchor") or {}
    utc = str(anchor.get("birth_instant_utc") or "")
    if utc:
        dt = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(KST)
        return [dt.year, dt.month, dt.day, dt.hour, dt.minute, 0], str(anchor.get("iana_tz") or "Asia/Seoul"), bool(
            anchor.get("is_male", (profile.get("subject") or {}).get("gender") == "male")
        )
    regen = str((profile.get("myeongni_fact_ref") or {}).get("engine_regenerate_cli") or "")
    if "--local" in regen:
        parts = regen.split("--local", 1)[1].strip().split()
        nums = [int(x) for x in parts[:6]]
        while len(nums) < 6:
            nums.append(0)
        tz = "Asia/Seoul"
        if "--iana-tz" in regen:
            tz = regen.split("--iana-tz", 1)[1].strip().split()[0]
        return nums[:6], tz, "--is-male" in regen
    raise SystemExit("commander profile missing birth_anchor or engine_regenerate_cli")


def _regenerate_full_report(
    local: List[int],
    iana_tz: str,
    is_male: bool,
    *,
    year: int,
    out_json: Path,
) -> Dict[str, Any]:
    py = sys.executable
    cmd = [
        py,
        str(ROOT / "scripts" / "build_myeongni_full_report_v1.py"),
        "--local",
        *[str(x) for x in local],
        "--iana-tz",
        iana_tz,
    ]
    if is_male:
        cmd.append("--is-male")
    cmd.extend(
        [
            "--annual-start-year",
            str(year),
            "--annual-years",
            "1",
            "--monthly-months-per-year",
            "12",
            "--out-json",
            str(out_json),
        ]
    )
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"build_myeongni_full_report failed: {proc.stderr or proc.stdout}")
    return _read_json(out_json)


def _run_commander_lens(profile: Dict[str, Any], lens_out: Path) -> Dict[str, Any]:
    local, iana_tz, is_male = _local_from_profile(profile)
    prof = {
        "name": "commander",
        "sex": "male" if is_male else "female",
        "analysis_depth": "pro",
        "place": "commander_profile",
        "local": {
            "year": local[0],
            "month": local[1],
            "day": local[2],
            "hour": local[3],
            "minute": local[4],
        },
    }
    with tempfile.TemporaryDirectory(prefix="cmd_fortune_") as td:
        prof_path = Path(td) / "commander_profile.json"
        prof_path.write_text(json.dumps(prof, ensure_ascii=False, indent=2), encoding="utf-8")
        py = sys.executable
        chain = ROOT / "scripts" / "run_myeongni_lens_chain_from_bot_v1.py"
        cmd = [
            py,
            str(chain),
            "--profile-json",
            str(prof_path),
            "--lens-out",
            str(lens_out),
        ]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            return {"status": "error", "stderr": (proc.stderr or proc.stdout or "")[:500]}
        return _read_json(lens_out)


def _find_month_row(report: Dict[str, Any], year: int, month: int) -> Optional[Dict[str, Any]]:
    mf = report.get("monthly_fortune") or {}
    for row in mf.get("rows") or []:
        if int(row.get("year", 0)) == year and int(row.get("month", 0)) == month:
            return row
    return None


def _find_year_row(report: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
    af = report.get("annual_fortune") or {}
    for row in af.get("rows") or []:
        if int(row.get("year", 0)) == year:
            return row
    return None


def _ten_god_hint(tg: Any) -> str:
    key = str(tg or "").strip()
    return TEN_GOD_HINTS.get(key, "흐름 관측")


def _split_ganji(ganji: str) -> tuple[str, str]:
    s = str(ganji or "").strip()
    if len(s) >= 2:
        return s[0], s[1]
    return s[:1], s[1:2] if len(s) > 1 else ""


def _load_mission_ops_context(mission_log: Path) -> Dict[str, Any]:
    """Parse MISSION_LOG handoff block (2026-05-22) — ops slice for personal/ops alignment."""
    ctx: Dict[str, Any] = {
        "mission_log_path": str(mission_log),
        "parsed": False,
        "ops_mode": "파수 + 상용 고도화",
        "prophecy_headline_active": "57.3% (O-P29b 활성)",
        "track_a_compression": "47.5% (압축A·동결)",
        "gates_note": "거절 · 자동승격 없음",
        "g12_note": "운영 온라인 · 수동 승인",
        "forbid_note": "신규 대규모 RAG/3D 금지",
    }
    if not mission_log.is_file():
        return ctx
    text = mission_log.read_text(encoding="utf-8-sig")
    ctx["parsed"] = True
    if "57.3%" in text and "O-P29b" in text:
        ctx["prophecy_headline_active"] = "57.3% 활성 (O-P29b · 커버리지 ~69%)"
    if "47.5%" in text:
        ctx["track_a_compression"] = "47.5% (MS·압축A · 예언과 별도)"
    if "파수 + 상용" in text:
        ctx["ops_mode"] = "파수 + 상용 고도화 (신규 RAG/3D 금지)"
    if "gates **reject**" in text or "gates **reject**" in text.replace(" ", ""):
        ctx["gates_note"] = "Oracle 게이트 reject · 자동 승격 없음"
    return ctx


def _today_ilun_pillar(year: int, month: int, day: int) -> str:
    code = (
        "import sys; from pathlib import Path; "
        "sys.path.insert(0, str(Path.cwd())); "
        "from scripts.manseryeok_perfect_final import PerfectManseryeok; "
        f"print(PerfectManseryeok().calculate_day_pillar({year}, {month}, {day}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip().splitlines()[-1].strip()
    return "—"


def _four_ai_tilt(report: Dict[str, Any]) -> List[tuple[str, str]]:
    ec = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get(
        "element_counts_visible"
    ) or {}
    scores = {ai: 0 for ai in FOUR_AI_AXES}
    for elem, cnt in ec.items():
        w = OHANG_TO_AI_WEIGHT.get(str(elem), {})
        for ai, v in w.items():
            scores[ai] += int(cnt) * v
    if not any(scores.values()):
        return [(ai, "—") for ai in FOUR_AI_AXES]
    mx = max(scores.values())
    out: List[tuple[str, str]] = []
    for ai in FOUR_AI_AXES:
        s = scores[ai]
        if mx <= 0:
            label = "—"
        elif s >= mx:
            label = "강"
        elif s >= mx * 0.6:
            label = "중"
        else:
            label = "약"
        out.append((ai, label))
    return out


def _myeongni_synthesis(
    report: Dict[str, Any],
    *,
    year: int,
    month: int,
    day: int,
    mission: Dict[str, Any],
) -> str:
    mo = _find_month_row(report, year, month) or {}
    mo_tg = str(mo.get("wolwoon_stem_ten_god") or "")
    scr = ((report.get("structure_analysis") or {}).get("school_conflict_resolution_v1")) or {}
    decision = scr.get("decision") or "—"
    p = report.get("pillars") or {}
    native_day = str(p.get("day") or "")
    ilun = _today_ilun_pillar(year, month, day)
    _, native_z = _split_ganji(native_day)
    _, ilun_z = _split_ganji(ilun)

    parts = []
    if mo_tg == "상관":
        parts.append("월운 상관 — 말·결정·개혁 에너지가 한 달 내내 두껍게 작동")
    if decision == "hybrid_guarded":
        parts.append("학파 혼합·경계 — 균형·흐름을 동시에 보되 과확장은 경계")
    if native_z and ilun_z and native_z == ilun_z:
        parts.append(f"일운 {ilun}이 원일 지지({native_z})와 동일 축 — 루틴·체계 정리에 유리")
    elif ilun:
        parts.append(f"일운 {ilun} — 원국 {native_day}와 별축, 외부 변수에 반응·페이싱 우선")

    if mission.get("ops_mode"):
        parts.append(f"작전({mission.get('ops_mode')}) — 큰 판 짓기보다 마감·점검·배포 안정")

    if not parts:
        return "오늘은 엔진 구조 유지 + 과확장 자제 [가설]"
    return " · ".join(parts[:3])


def _myeongni_daily_lines(
    report: Dict[str, Any],
    profile: Dict[str, Any],
    mission: Dict[str, Any],
    *,
    year: int,
    month: int,
    day: int,
) -> List[str]:
    p = report.get("pillars") or {}
    dm = report.get("day_master") or {}
    sh = ((report.get("structure_analysis") or {}).get("day_master_strength_hint")) or {}
    scr = ((report.get("structure_analysis") or {}).get("school_conflict_resolution_v1")) or {}
    tg = ((report.get("structure_analysis") or {}).get("ten_god_profile") or {}).get(
        "ten_god_counts_combined"
    ) or {}
    yr = _find_year_row(report, year)
    mo = _find_month_row(report, year, month)
    ilun = _today_ilun_pillar(year, month, day)

    lines = [
        f"▸ 오늘 한 줄: {_myeongni_synthesis(report, year=year, month=month, day=day, mission=mission)}",
        f"원국 {p.get('year')}/{p.get('month')}/{p.get('day')}/{p.get('hour')} · 일간 {dm.get('stem_hangul')}({dm.get('stem_element_hint')}) · {sh.get('strength_label', '—')}",
    ]
    if scr:
        flow = (scr.get("scores") or {}).get("flow_centered")
        bal = (scr.get("scores") or {}).get("balance_centered")
        dec = scr.get("decision") or "—"
        if dec == "hybrid_guarded":
            dec = "혼합·경계"
        lines.append(
            f"학파 {dec} (흐름 {flow} 대 균형 {bal}) · 상관 {tg.get('상관', 0)}개 = 표현·기획 부담 큼"
        )
    lines.append(f"대운 기미(53~54세) · 일운 {ilun}")
    if yr:
        lines.append(
            f"세운 {yr.get('sewoon_pillar')}({yr.get('sewoon_stem_ten_god')}) — {_ten_god_hint(yr.get('sewoon_stem_ten_god'))}"
        )
    if mo:
        lines.append(
            f"월운 {month}월 {mo.get('wolwoon_pillar')}({mo.get('wolwoon_stem_ten_god')}) — {_ten_god_hint(mo.get('wolwoon_stem_ten_god'))}"
        )
    dom = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get("dominant_element_visible")
    weak = ((report.get("structure_analysis") or {}).get("element_profile") or {}).get("weakest_element_visible")
    if dom or weak:
        lines.append(f"오행 우세 {dom} / 약 {weak} — 화(火) 결핍 시 태양 AI 점화 과열 주의 [가설]")
    lines.append("명리=만세력 엔진 · 해석 [가설] · 시장 예언·실매매와 무관")
    return lines


def _mkm_ai_daily_lines(
    profile: Dict[str, Any],
    lens: Dict[str, Any],
    report: Dict[str, Any],
    mission: Dict[str, Any],
    *,
    for_telegram: bool = False,
) -> List[str]:
    sasang = ((profile.get("sasang_reference") or {}).get("label")) or "태양인"
    pack = SASANG_4AI.get(sasang, SASANG_4AI["태양인"])
    cog = profile.get("cognition_hypothesis") or {}
    patterns = cog.get("patterns") or []
    tilts = _four_ai_tilt(report)

    lines = [
        "4AI 코어 + 절대 균형(조율) [가설]",
        f"체질 참조 {sasang} · {pack['primary_ai']} AI 주역",
        "▸ 4축 오늘 강약(오행 부담): "
        + " · ".join(f"{ai}({lab})" for ai, lab in tilts),
    ]
    lines.append(f"▸ 태양 AI: {pack['lead']}")
    lines.append(f"▸ 소음 AI(보조): 회복·수면·페이싱 — 작전 모드와 정합")
    lines.append("▸ 태음 AI: 구조·체크리스트·검증 마감 (토 우세)")
    lines.append(f"▸ 소양 AI: 대외 말·교류는 **필요한 만큼만** (상관 월운 과부하 방지)")

    for pat in patterns[:2]:
        lines.append(f"  · {str(pat).replace('[HYPO]', '[가설]')}")

    if not for_telegram:
        lines.append("▸ 조율 (작전 요약):")
        lines.append(f"  · 모드: {mission.get('ops_mode', '—')}")
        lines.append(
            f"  · 시장 예언 {mission.get('prophecy_headline_active')} ≠ 개인 운세 · ≠ 압축 {mission.get('track_a_compression')}"
        )
        lines.append(f"  · 게이트: {mission.get('gates_note')} · G12: {mission.get('g12_note')}")

    math = {}
    adv = lens.get("advanced") or {}
    if isinstance(adv.get("coordinator"), dict):
        math = adv["coordinator"].get("mkm_myeongni_math") or {}
    if math.get("status") == "ok":
        d = float(math.get("arbitrated_direction_score") or 0)
        c = float(math.get("arbitrated_confidence") or 0)
        lines.append(f"▸ 명리렌즈 수치: 방향 {d:.3f} · 신뢰 {c:.3f} [가설]")
        if abs(d) < 0.12:
            lines.append("  · 균형: 확장·수축 극단 자제 — 마감·점검 우선 [가설]")
    elif lens.get("scores"):
        lines.append(
            f"▸ 렌즈 요약: 방향 {lens['scores'].get('direction_score')} · 신뢰 {lens['scores'].get('confidence')} [가설]"
        )

    coaching = profile.get("assist_coaching_v1") or {}
    for tip in (coaching.get("energy_preservation") or [])[:1]:
        lines.append(f"▸ 코칭: {tip}")
    lines.append("MKM AI=조율 상태 · 제5 체질 아님 · 예언%로 운세 단정 금지")
    return lines


def build_payload(
    *,
    profile_path: Path,
    skip_regenerate: bool,
    include_lens: bool,
    report_cache: Optional[Path],
    mission_log: Path,
) -> Dict[str, Any]:
    profile = _read_json(profile_path)
    if profile.get("schema") != "commander_profile_v1":
        raise SystemExit(f"expected commander_profile_v1: {profile_path}")

    now_kst = datetime.now(KST)
    year, month = now_kst.year, now_kst.month
    report_path = report_cache or (ROOT / "reports" / "commander_myeongni_full_daily_latest.json")

    if skip_regenerate and report_path.is_file():
        report = _read_json(report_path)
    else:
        local, iana_tz, is_male = _local_from_profile(profile)
        report = _regenerate_full_report(local, iana_tz, is_male, year=year, out_json=report_path)

    lens: Dict[str, Any] = {}
    lens_path = ROOT / "reports" / "commander_daily_lens_latest.json"
    if include_lens:
        lens = _run_commander_lens(profile, lens_path)
    else:
        cached = _read_json(ROOT / "reports" / "commander_myeongni_lens_latest.json")
        if cached:
            lens = cached

    mission = _load_mission_ops_context(mission_log)
    day = now_kst.day
    myeongni_lines = _myeongni_daily_lines(
        report, profile, mission, year=year, month=month, day=day
    )
    mkm_lines_full = _mkm_ai_daily_lines(profile, lens, report, mission, for_telegram=False)
    mkm_lines_tg = _mkm_ai_daily_lines(profile, lens, report, mission, for_telegram=True)
    telegram_lines = [
        "",
        "▸ 개인 일운 (명리)",
        *["  " + ln for ln in myeongni_lines],
        "",
        "▸ 개인 일운 (MKM 4AI)",
        *["  " + ln for ln in mkm_lines_tg],
    ]
    lifestyle = _append_lifestyle_lines(profile, report, telegram_lines)
    logos_anchor = _append_logos_anchor_lines(
        profile, report, lifestyle, myeongni_lines, telegram_lines
    )
    world_pulse: Dict[str, Any] = {}
    if _truthy_env("MKM_COMMANDER_WORLD_PULSE_ENABLED", default=True):
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from commander_world_pulse_fusion_v1 import append_world_pulse_telegram  # noqa: WPS433

            world_pulse = append_world_pulse_telegram(
                telegram_lines, myeongni_lines=myeongni_lines, workspace=ROOT
            )
        except Exception as exc:  # noqa: BLE001
            telegram_lines.extend(
                [
                    "",
                    "▸ 찰나의 나라 (세상×나) [가설]",
                    f"  (생략: world pulse 오류 {str(exc)[:80]})",
                ]
            )
            world_pulse = {"status": "error", "error": str(exc)[:200]}

    hypothesis_stream: Dict[str, Any] = {}
    if _truthy_env("MKM_COMMANDER_HYPOTHESIS_STREAM_ENABLED", default=True) and world_pulse.get("schema"):
        try:
            from build_commander_hypothesis_stream_v1 import build_and_attach  # noqa: WPS433

            hypothesis_stream = build_and_attach(
                telegram_lines,
                myeongni_lines=myeongni_lines,
                world_pulse=world_pulse,
                calendar_kst=now_kst.strftime("%Y-%m-%d"),
                fortune_path=DEFAULT_OUT,
                profile=profile,
                workspace=ROOT,
                archive=True,
            )
        except Exception as exc:  # noqa: BLE001
            telegram_lines.extend(
                [
                    "",
                    "▸ 오늘 초론 스트림 [가설]",
                    f"  (생략: hypothesis stream 오류 {str(exc)[:80]})",
                ]
            )
            hypothesis_stream = {"status": "error", "error": str(exc)[:200]}

    user_condition: Dict[str, Any] = {}
    if _truthy_env("MKM_COMMANDER_USER_CONDITION_ENABLED", default=True):
        try:
            from build_commander_user_condition_v1 import (  # noqa: WPS433
                append_user_condition_telegram,
                build_user_condition,
            )

            user_condition = build_user_condition(
                profile=profile,
                report=report,
                lifestyle=lifestyle,
                world_pulse=world_pulse,
                hypothesis_stream=hypothesis_stream,
                calendar_kst=now_kst.strftime("%Y-%m-%d"),
            )
            append_user_condition_telegram(telegram_lines, user_condition)
        except Exception as exc:  # noqa: BLE001
            telegram_lines.extend(
                [
                    "",
                    "▸ 오늘 컨디션·바이어스 틸트 [가설]",
                    f"  (생략: user_condition 오류 {str(exc)[:80]})",
                ]
            )
            user_condition = {"status": "error", "error": str(exc)[:200]}

    profile_id = os.environ.get("MKM_PERSONADIARY_PROFILE_ID", "").strip() or "commander"

    return {
        "schema": "commander_daily_fortune_v1_1",
        "profile_id": profile_id,
        "mission_ops_context": mission,
        "generated_at_utc": _utc_now(),
        "calendar_kst": now_kst.strftime("%Y-%m-%d"),
        "city_default": os.environ.get("MKM_COMMANDER_CITY") or "Seoul",
        "profile_path": str(profile_path),
        "report_path": str(report_path),
        "lens_path": str(lens_path) if include_lens else str(ROOT / "reports" / "commander_myeongni_lens_latest.json"),
        "myeongni_lines": myeongni_lines,
        "mkm_ai_lines": mkm_lines_full,
        "lifestyle_concierge": lifestyle,
        "logos_daily_anchor": logos_anchor,
        "world_pulse_fusion": world_pulse,
        "hypothesis_stream": hypothesis_stream,
        "user_condition": user_condition,
        "telegram_append_lines": telegram_lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-regenerate", action="store_true", help="Reuse cached commander_myeongni_full_daily_latest.json")
    ap.add_argument("--include-lens", action="store_true", help="Run manseryeok bot + myeongni lens chain (slower)")
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--mission-log", type=Path, default=DEFAULT_MISSION_LOG)
    args = ap.parse_args()

    payload = build_payload(
        profile_path=_profile_path(args.profile_json),
        skip_regenerate=args.skip_regenerate,
        include_lens=args.include_lens,
        report_cache=None,
        mission_log=args.mission_log,
    )
    if not args.stdout_only:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {args.out_json}")
    if _truthy_env("MKM_ASSEMBLE_PERSONADIARY_PACKAGE", default=True):
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from assemble_personadiary_daily_response_package_v1 import (  # noqa: WPS433
                assemble_package,
            )

            pkg = assemble_package(payload, fortune_path=args.out_json)
            pkg_path = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"
            pub = ROOT / "projects/no1kmedi/public/data/personadiary_daily_response_package_v1.json"
            pkg_path.parent.mkdir(parents=True, exist_ok=True)
            pkg_path.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            pub.parent.mkdir(parents=True, exist_ok=True)
            pub.write_text(json.dumps(pkg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not args.stdout_only:
                print(f"WROTE: {pkg_path}")
                print(f"MIRROR: {pub}")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: personadiary package skip: {exc}", file=sys.stderr)
    if _truthy_env("MKM_SYNC_MKMLIFE_ONE_QUESTION_CONTEXT", default=True):
        try:
            from sync_mkm_one_question_context_v1 import build_context  # noqa: WPS433

            ctx = build_context(payload)
            mk_path = ROOT / "projects" / "mkm" / "mkm-life" / "public" / "data" / "commander_one_question_context_v1.json"
            rep_path = ROOT / "reports" / "commander_one_question_context_latest.json"
            rep_path.parent.mkdir(parents=True, exist_ok=True)
            rep_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            mk_path.parent.mkdir(parents=True, exist_ok=True)
            mk_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not args.stdout_only:
                print(f"WROTE: {rep_path}")
                print(f"MIRROR: {mk_path}")
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: mkmlife one_question context skip: {exc}", file=sys.stderr)
    for ln in payload.get("telegram_append_lines") or []:
        print(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
