#!/usr/bin/env python3
"""Daily Telegram premarket digest — compact or advanced (KOSPI brief + dual-leg + ops)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
TELEGRAM_MAX_LEN = 4096


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        val = val.strip().strip('"').strip("'")
        if key:
            os.environ[key] = val


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _resolve_secret(name: str) -> str:
    """Process/.env first, then Security Agent (DPAPI). Never log values."""
    direct = os.getenv(name, "").strip()
    if direct:
        return direct
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from security_agent_manager import get_security_agent  # type: ignore

        got = get_security_agent().get_env_var(name)
        if got and str(got).strip():
            return str(got).strip()
    except Exception:
        pass
    return ""


def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, f"http_{resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"http_{exc.code}:{exc.read()[:200]!r}"
    except Exception as exc:  # pragma: no cover
        return False, f"error:{exc}"


def _fmt_pct(v: Any) -> str:
    try:
        if v is None:
            return "없음"
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "없음"


def _fmt_kst_from_utc(iso: Any) -> str:
    if not iso:
        return "—"
    raw = str(iso).strip()
    if not raw:
        return "—"
    try:
        if raw.endswith("Z"):
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")
    except (TypeError, ValueError):
        return raw[:19]


def _leg_metrics(dual_leg: Dict[str, Any], tag: str) -> tuple[Optional[int], Any]:
    leg = (dual_leg.get("legs") or {}).get(tag) or {}
    return leg.get("n_evaluated"), leg.get("price_directional_hit_rate")


def _koreanize_personal_line(line: str) -> str:
    """Strip common English ops tokens from fortune lines (display only)."""
    repl = (
        ("hybrid_guarded", "혼합·경계"),
        ("Absolute Balance", "절대 균형"),
        ("Coordinator", "조율"),
        ("Fact-Lock", "팩트락"),
        ("fact-lock", "팩트락"),
        ("Fact ·", "팩트 ·"),
        ("MISSION_LOG", "작전로그"),
        ("combined_all_passed false", "자동승격 없음"),
        ("reject ·", "거절 ·"),
        ("PM2 online", "운영 온라인"),
        ("human gate", "수동 승인"),
        ("ACTIVE", "활성"),
        ("Track A", "압축A"),
        ("· dir ", "· 방향 "),
        ("· conf ", "· 신뢰 "),
        ("dir ", "방향 "),
        (" conf ", " 신뢰 "),
        (" vs ", " 대 "),
        ("GO와", "실행허가와"),
        ("GO ", "실행허가 "),
        ("(MKM 4AI + Coordinator)", "(MKM 4AI + 조율)"),
        ("internal_only", ""),
        ("[HYPO]", "[가설]"),
        ("(Logos)", "(성경)"),
        ("weather_band:mild", "날씨밴드:온화"),
        ("weather_band:", "날씨밴드:"),
        ("weakest_element:", "약오행:"),
        ("sasang:", "체질:"),
        ("Logos ", "성경 "),
        ("Logos 관측", "성경 관측"),
        ("NON_GATING", "비게이팅"),
        ("RAG/3D", "검색·3D"),
        ("· WATCH ·", "· 주시 ·"),
        ("장면: WATCH", "장면: 주시"),
        ("거시 WATCH", "거시 주시"),
        ("판: 장면 WATCH", "판: 장면 주시"),
        ("post covid normalization", "코로나 이후 정상화"),
        ("watch_tighten", "관측·긴축"),
        ("market_liquidity_stress", "시장 유동성 스트레스"),
        ("elevated", "상향"),
        ("veto_hold=False", "거부홀드=아니오"),
        ("bull", "상승"),
        ("bear", "하락"),
        ("myeongni=", "명리="),
        ("sasang=", "사상="),
        ("logos=", "성경="),
        (" mild ", " 온화 "),
        (" mid ", " 중간 "),
        ("n/a", "없음"),
        ("pass_candidate", "합격후보"),
        ("manual_review_candidate", "수동검토후보"),
        ("directional_bull", "방향상승"),
        ("directional_bear", "방향하락"),
        ("directional_neutral", "방향중립"),
        ("pending", "대기"),
        ("scored", "채점완료"),
        ("WF mean", "평균"),
        ("stdev", "기복"),
        ("streak", "연속합격"),
        ("Field Final Call", "실물·최종판단"),
        ("Final Call", "최종판"),
        ("attach ", "부착 "),
        ("posture ", "자세 "),
        ("sidebar", "보조"),
        ("NON_GATING", "비게이팅"),
        ("Mission C", "미션C"),
        ("GO_CONDITIONAL", "조건부실행"),
        ("GO_FINAL_V2", "최종승격v2"),
        ("HOLD_OPERATIONAL_V1", "운영유지v1"),
        ("sealed_today", "오늘봉인"),
        ("R-IBL", "연구봉인"),
        ("seal=", "봉인="),
    )
    out = line
    for old, new in repl:
        out = out.replace(old, new)
    return out


def _sanitize_telegram_ko(text: str) -> str:
    """Final pass: prophecy/personal digest lines — strip stray English ops tokens."""
    lines = []
    for raw in text.splitlines():
        lines.append(_koreanize_personal_line(raw))
    return "\n".join(lines)


def build_digest_personal(workspace: Path) -> str:
    """지휘관 개인 일운(명리·4AI·라이프)만 — 예언/KOSPI/BTC/VPS 블록 없음."""
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M") + " 한국시"
    city = os.getenv("MKM_COMMANDER_CITY", "Seoul").strip() or "Seoul"
    lines: List[str] = [f"지휘관 오늘 일운 · {now_kst} · {city}", ""]

    if not fortune_path.is_file():
        lines.append("(일운 없음 — 먼저 py scripts/build_commander_daily_fortune_v1.py 실행)")
        return "\n".join(lines)

    doc = _read_json(fortune_path)
    schema = doc.get("schema") or ""
    if schema not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        lines.append(f"(스키마 불일치: {schema})")
        return "\n".join(lines)

    skip_ops = _truthy("MKM_TELEGRAM_PERSONAL_SKIP_OPS_BLOCK", default=True)
    in_ops_block = False
    for ln in doc.get("telegram_append_lines") or []:
        if not ln:
            lines.append("")
            in_ops_block = False
            continue
        if "조율)" in ln or "Coordinator" in ln or "작전 SSOT" in ln:
            in_ops_block = True
        if skip_ops and in_ops_block:
            if ln.strip().startswith("▸") and "조율" not in ln and "Coordinator" not in ln:
                in_ops_block = False
            else:
                continue
        if skip_ops and ("시장 예언" in ln or "게이트:" in ln or "렌즈 스텁" in ln):
            continue
        lines.append(_koreanize_personal_line(ln))

    text = "\n".join(lines).strip()
    if len(text) > TELEGRAM_MAX_LEN:
        return text[: TELEGRAM_MAX_LEN - 20] + "\n…(잘림)"
    return text


_CHANNEL_KO = {
    "session_myeongni": "세션명리",
    "myeongni_independent": "명리",
    "sasang": "사상",
    "macro": "거시",
    "logos_non_gating": "성경",
    "field_regime": "레짐",
    "momentum_overlay": "모멘텀",
    "ensemble_kospi_causal": "인과앙상블",
}


def _ko_channel(channel: Any) -> str:
    raw = str(channel or "—").strip()
    return _CHANNEL_KO.get(raw, raw.replace("_", " "))


def _truncate_telegram(text: str) -> str:
    if len(text) <= TELEGRAM_MAX_LEN:
        return text
    return text[: TELEGRAM_MAX_LEN - 20] + "\n…(잘림)"


def _append_telegram_lines_from_doc(
    lines: List[str],
    doc: Dict[str, Any],
    *,
    indent: str = "  ",
) -> None:
    for ln in doc.get("telegram_append_lines") or []:
        if ln is None:
            lines.append("")
            continue
        stripped = str(ln).strip()
        if not stripped:
            lines.append("")
            continue
        if stripped.startswith("▸"):
            lines.append(_koreanize_personal_line(stripped))
        else:
            lines.append(indent + _koreanize_personal_line(stripped.lstrip()))


def _append_fortune_detail(lines: List[str], fortune: Dict[str, Any], *, depth: str = "full") -> None:
    """depth: full (오후) | compact (장전 한 줄 요약)."""
    if fortune.get("schema") not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        lines.append("  (일운 없음 — build_commander_daily_fortune_v1.py 실행 필요)")
        return

    prof_path = fortune.get("profile_path")
    prof = _read_json(Path(str(prof_path))) if prof_path else {}
    anchor = (prof.get("birth_anchor") or {}) if prof else {}
    pillars = ((prof.get("myeongni_fact_ref") or {}).get("pillars") or {}) if prof else {}
    sasang = ((prof.get("sasang_reference") or {}).get("label") or "") if prof else ""

    if pillars:
        lines.append(
            f"  원국 {pillars.get('year')}/{pillars.get('month')}/"
            f"{pillars.get('day')}/{pillars.get('hour')}"
        )
    if anchor.get("local_label"):
        lines.append(f"  출생 {anchor.get('local_label')}")
    if sasang:
        lines.append(f"  체질 참조 {sasang} [가설]")

    myeongni_cap = 3 if depth == "compact" else 20
    for ln in (fortune.get("myeongni_lines") or [])[:myeongni_cap]:
        if ln:
            lines.append(f"  {_koreanize_personal_line(ln)}")

    if depth == "full":
        lines.append("")
        lines.append("▸ MKM 4AI·조율 [가설]")
        for ln in fortune.get("mkm_ai_lines") or []:
            if ln:
                lines.append(f"  {_koreanize_personal_line(ln)}")

        lc = fortune.get("lifestyle_concierge") or {}
        if lc:
            lines.append("")
            _append_telegram_lines_from_doc(lines, lc)

        lo = fortune.get("life_oracle") or {}
        if lo:
            _append_telegram_lines_from_doc(lines, lo)

        logos = fortune.get("logos_daily_anchor") or {}
        if logos:
            _append_telegram_lines_from_doc(lines, logos)

        wp = fortune.get("world_pulse_fusion") or {}
        if wp:
            lines.append("")
            lines.append("▸ 오늘 판(코스피·거시) [가설·관측]")
            k = wp.get("kospi") or {}
            if k:
                lines.append(
                    f"  코스피 {_ko_market_action(k.get('today_action'))} · 확신 {k.get('confidence_0_100')}/100"
                    f" · 적중 {_fmt_pct(k.get('hit_rate'))} (n={k.get('n_evaluated')})"
                )
            m = wp.get("macro") or {}
            if m:
                lines.append(
                    f"  거시 {_ko_market_action(m.get('decision_state'))} · 리스크 {_ko_risk_level(m.get('risk_warning_level'))}"
                    f" · 판 {str(m.get('primary_regime_id', '')).replace('_', ' ')}"
                )
            n = wp.get("news") or {}
            if n.get("direction_score") is not None:
                lines.append(f"  뉴스 렌즈 점수 {n.get('direction_score')} · 신뢰 {n.get('confidence')}")
    else:
        for ln in fortune.get("mkm_ai_lines") or []:
            if ln and "코칭" in str(ln):
                lines.append(f"  {_koreanize_personal_line(ln)}")
                break


def _append_kospi_date_detail(
    lines: List[str],
    workspace: Path,
    session_date: str,
    *,
    brief: Optional[Dict[str, Any]] = None,
    hypo: Optional[Dict[str, Any]] = None,
) -> None:
    cal_row = _calendar_row_for_date(workspace, session_date)
    four_ai = _four_ai_row_for_date(workspace, session_date)
    brief = brief or {}

    weekday = cal_row.get("weekday_ko") or four_ai.get("weekday_ko") or ""
    title = f"▸ 코스피 {session_date} 예측"
    if weekday:
        title += f" ({weekday})"
    lines.extend(["", title])

    if not cal_row and not four_ai:
        lines.append("  (6월 캘린더·4AI 행 없음)")
        return

    if cal_row:
        dir_ko = cal_row.get("predicted_direction_ko") or _ko_direction(cal_row.get("predicted_direction"))
        lines.append(
            f"  멀티렌즈 방향 {dir_ko} · 점수 {cal_row.get('session_direction_score')}"
            f" · 상태 {_ko_calendar_status(cal_row.get('status'))}"
        )
        pillars = cal_row.get("pillars_session") or {}
        if pillars:
            lines.append(
                f"  세션 사주 {pillars.get('year')}/{pillars.get('month')}/"
                f"{pillars.get('day')}/{pillars.get('hour')}"
            )
        blend = cal_row.get("blend") or {}
        votes = blend.get("votes") or {}
        if votes:
            lines.append(
                f"  투표 합의 상승 {votes.get('bull')} · 하락 {votes.get('bear')} · 중립 {votes.get('neutral')}"
                f" → {_ko_winner_resolution(blend.get('winner_resolution'))}"
            )
        channels = blend.get("channels") or []
        active = [c for c in channels if isinstance(c, dict) and float(c.get("weight") or 0) > 0]
        if active:
            lines.append("  렌즈 채널:")
            for ch in active:
                meta = ch.get("meta") if isinstance(ch.get("meta"), dict) else {}
                score = meta.get("score")
                score_s = f" · 점수 {float(score):.3f}" if score is not None else ""
                lines.append(
                    f"    · {_ko_channel(ch.get('channel'))} "
                    f"{_ko_direction(ch.get('direction'))} · 가중 {ch.get('weight')}{score_s}"
                )
        if cal_row.get("status") == "scored":
            lines.append(
                f"  장 마감 실제 {cal_row.get('actual_direction_ko') or _ko_direction(cal_row.get('actual_direction'))}"
                f" ({cal_row.get('actual_return_pct')}%) · "
                f"{'적중' if cal_row.get('hit') else '오적' if cal_row.get('hit') is False else '—'}"
            )

    if four_ai:
        lines.append("  4AI 코어:")
        for agent in four_ai.get("four_ai_agents") or []:
            if not isinstance(agent, dict):
                continue
            ch_bits: List[str] = []
            for ch in (agent.get("channels") or [])[:3]:
                if not isinstance(ch, dict):
                    continue
                w = ch.get("weight")
                if w is not None and float(w) <= 0:
                    continue
                ch_bits.append(f"{_ko_channel(ch.get('channel'))}:{_ko_direction(ch.get('direction'))}")
            ch_s = f" ({', '.join(ch_bits)})" if ch_bits else ""
            score = agent.get("score")
            score_s = f" · {float(score):.3f}" if score is not None else ""
            lines.append(
                f"    · {agent.get('label_ko')} → {agent.get('direction_ko')}{score_s}{ch_s}"
            )
        ab = four_ai.get("absolute_balance") or {}
        if ab:
            split = ab.get("agent_vote_split") or {}
            cc = ab.get("channel_consensus") or {}
            lines.append(
                f"  절대균형(조율) 갈등 {ab.get('conflict_score')} · "
                f"에이전트 투표 상{split.get('bull', 0)} 중{split.get('neutral', 0)} 하{split.get('bear', 0)}"
            )
            if cc.get("direction_ko"):
                lines.append(f"  채널 합의 {cc.get('direction_ko')} · 평균점수 {ab.get('agent_mean_score')}")

    if hypo:
        pred = hypo.get("prediction") or {}
        if pred:
            inst = str(pred.get("instrument") or "—").upper()
            inst_ko = {"KOSPI": "코스피", "BTC": "비트코인", "MULTI": "멀티"}.get(inst, inst)
            conf = pred.get("confidence")
            ws = pred.get("weighted_score")
            extra = ""
            if conf is not None:
                extra += f" · 신뢰 {float(conf):.2f}"
            if ws is not None:
                extra += f" · 가중 {float(ws):.4f}"
            lines.append(
                f"  B트랙 가설 {inst_ko} · 방향 {_ko_direction(pred.get('direction'))}{extra}"
            )

    bh = brief.get("btrack_hypothesis") if isinstance(brief.get("btrack_hypothesis"), dict) else {}
    if brief.get("today_action"):
        conf = brief.get("confidence_0_100")
        lines.append(
            f"  장전 브리프 {_ko_market_action(brief.get('today_action'))}"
            + (f" · 확신 {conf}/100" if conf is not None else "")
            + (f" · 거버넌스 {brief.get('governance_confidence_0_100')}/100" if brief.get("governance_confidence_0_100") else "")
        )
    if bh.get("composite_tilt"):
        lines.append(f"  오버나이트 틸트 {_ko_composite_tilt(bh.get('composite_tilt'))}")


def _calendar_row_for_date(workspace: Path, session_date: str) -> Dict[str, Any]:
    for name in (
        "kospi_june2026_daily_prophecy_calendar_v1.json",
        "kospi_202606_daily_prophecy_calendar_v1.json",
    ):
        cal = _read_json(workspace / "reports" / name)
        for row in cal.get("rows") or []:
            if isinstance(row, dict) and row.get("session_date") == session_date:
                return row
    return {}


def _four_ai_row_for_date(workspace: Path, session_date: str) -> Dict[str, Any]:
    report = _read_json(workspace / "reports" / "kospi_june2026_4ai_prophecy_report_latest.json")
    for row in report.get("sessions") or report.get("rows") or []:
        if isinstance(row, dict) and row.get("session_date") == session_date:
            return row
    return {}


def build_digest_afternoon(workspace: Path) -> str:
    """오후 한글 브리핑 — 지휘관 사주·일운(상세) + 코스피 예측·채널 [HYPO]."""
    cal_kst = datetime.now(KST).strftime("%Y-%m-%d")
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M") + " 한국시"
    art = workspace / "docs" / "final" / "artifacts"

    lines: List[str] = [
        f"MKM 오후 브리핑 · {now_kst}",
        "[가설] B트랙 · 실매매·압축A 자동 연동 없음",
        "",
        "▸ 지휘관 사주·일운",
    ]

    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    fortune = _read_json(fortune_path) if fortune_path.is_file() else {}
    _append_fortune_detail(lines, fortune, depth="full")

    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    hypo = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    _append_kospi_date_detail(lines, workspace, cal_kst, brief=brief, hypo=hypo)

    lines.extend(["", "실매매·Track A 자동 트리거 아님."])
    return _truncate_telegram("\n".join(lines))


def build_digest(workspace: Path, *, style: str = "minimal") -> str:
    if style == "personal":
        return build_digest_personal(workspace)
    if style == "prophecy":
        return build_digest_prophecy(workspace)
    if style == "afternoon":
        return build_digest_afternoon(workspace)
    if style == "advanced":
        return build_digest_advanced(workspace)
    if style == "evening_review":
        return build_digest_evening_review(workspace)
    return build_digest_minimal(workspace)


_FORTUNE_PROPHECY_STOP_MARKERS = (
    "▸ 찰나의 나라",
    "▸ 오늘 초론 스트림",
    "▸ 오늘 컨디션",
    "  ▸ cross-lens RAG",
    "  ▸ 4RAG",
)


def _fortune_lines_for_prophecy_morning(raw_lines: List[str]) -> List[str]:
    """Keep 명리·4AI·라이프·생활예언 only — drop world-pulse/RAG/hypothesis duplicates."""
    out: List[str] = []
    for ln in raw_lines:
        stripped = (ln or "").strip()
        if stripped and any(stripped.startswith(m) or m in stripped for m in _FORTUNE_PROPHECY_STOP_MARKERS):
            break
        out.append(ln)
    return out


def _append_personal_fortune(workspace: Path, lines: List[str]) -> None:
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    if not fortune_path.is_file():
        return
    doc = _read_json(fortune_path)
    schema = doc.get("schema") or ""
    if schema not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        return
    raw = doc.get("telegram_append_lines") or []
    for ln in _fortune_lines_for_prophecy_morning(raw):
        if ln:
            lines.append(_koreanize_personal_line(ln))


def _ko_market_action(action: Any) -> str:
    raw = str(action or "—").strip().upper()
    table = {
        "HOLD": "관망",
        "WATCH": "주시",
        "BULL": "상승",
        "BEAR": "하락",
        "REDUCE": "축소",
        "GO": "관측·허용",
        "GO_CONDITIONAL": "조건부실행",
        "NO_GO": "중단",
    }
    if raw in table:
        return table[raw]
    if raw.startswith("HOLD("):
        return raw.replace("HOLD", "관망", 1)
    return str(action or "—")


def _ko_direction(direction: Any) -> str:
    raw = str(direction or "—").strip().lower()
    table = {"bull": "상승", "bear": "하락", "neutral": "중립", "hold": "관망", "watch": "주시"}
    return table.get(raw, str(direction or "—"))


def _ko_composite_tilt(tilt: Any) -> str:
    raw = str(tilt or "—").strip()
    table = {
        "risk_off_overnight": "위험회피·오버나이트",
        "risk_on_overnight": "위험선호·오버나이트",
        "neutral_overnight": "중립·오버나이트",
    }
    return table.get(raw, raw.replace("_", " "))


def _fmt_lens_score(v: Any) -> str:
    try:
        if v is None:
            return "—"
        return f"{float(v):.3f}"
    except (TypeError, ValueError):
        return "—"


def _ko_risk_level(level: Any) -> str:
    raw = str(level or "—").strip().lower()
    return {"elevated": "상향", "normal": "보통", "low": "낮음", "high": "높음"}.get(raw, str(level or "—"))


def _ko_attach_mode(mode: Any) -> str:
    raw = str(mode or "—").strip().upper()
    return {"OFF": "끔", "ON": "켬", "WATCH": "관측"}.get(raw, raw.replace("_", " "))


def _ko_calendar_status(status: Any) -> str:
    raw = str(status or "—").strip().lower()
    return {
        "pending": "대기",
        "scored": "채점완료",
        "skipped": "생략",
        "sealed_today": "오늘봉인",
        "sealed": "봉인",
    }.get(raw, raw.replace("_", ""))


def _ko_promotion_decision(dec: Any) -> str:
    raw = str(dec or "—").strip()
    table = {
        "GO_FINAL_V2": "최종승격v2",
        "HOLD_OPERATIONAL_V1": "운영유지",
        "GO_CONDITIONAL": "조건부실행",
        "manual_review_candidate": "수동검토",
        "pass_candidate": "합격후보",
    }
    if raw in table:
        return table[raw]
    return raw.replace("_", "·")


def _ko_winner_resolution(res: Any) -> str:
    raw = str(res or "—").strip().lower()
    table = {
        "directional_bull": "방향상승",
        "directional_bear": "방향하락",
        "directional_neutral": "방향중립",
        "neutral_hold": "중립관망",
    }
    return table.get(raw, raw.replace("_", ""))


def _ko_outcome_class(outcome: Any) -> str:
    raw = str(outcome or "").strip().lower()
    return {
        "pass_candidate": "합격후보",
        "reject": "탈락",
        "neutral_bucket": "중립",
        "opportunistic": "기회관망",
    }.get(raw, raw.replace("_", ""))


def _ko_operator_posture(posture: Any) -> str:
    raw = str(posture or "—").strip()
    table = {
        "watch_tighten": "주시·긴장",
        "hold_calm": "관망·완화",
        "reduce_exposure": "노출 축소",
    }
    return table.get(raw, raw.replace("_", " "))


def _prophecy_slim_enabled() -> bool:
    return _truthy("MKM_TELEGRAM_PROPHECY_SLIM", default=False)


def _append_mission_c_shadow_telegram(lines: List[str], workspace: Path) -> None:
    """Mission C shadow one-liner — research_only; never operational headline."""
    if not _truthy("MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW", default=False):
        return
    ops = _read_json(workspace / "reports" / "mission_c_shadow_ops_status_v1_latest.json")
    if ops.get("schema") != "mission_c_shadow_ops_status_v1":
        return
    digest = ops.get("telegram_digest_block") if isinstance(ops.get("telegram_digest_block"), dict) else {}
    if not digest.get("enabled"):
        return
    gates = ops.get("gates") if isinstance(ops.get("gates"), dict) else {}
    streak = gates.get("strict_pass_streak")
    required = gates.get("strict_streak_required") or 5
    wf = ops.get("wf_aggregate") if isinstance(ops.get("wf_aggregate"), dict) else {}
    outcome = _ko_outcome_class(gates.get("outcome_class"))
    one_liner = (
        f"평균 {_fmt_pct(wf.get('mean_test_accuracy'))} · "
        f"기복 {_fmt_pct(wf.get('stdev_test_accuracy'))} · "
        f"연속합격 {streak}/{required}"
        + (f" · {outcome}" if outcome else "")
    )
    lines.extend(
        [
            "",
            "▸ 미션C 연습장 [가설]",
            f"  {one_liner}",
            "  본선 미변경 · 자동승격 없음",
        ]
    )


def _append_field_final_call_telegram(lines: List[str], brief: Dict[str, Any]) -> None:
    """Field-only Final Call block — lenses stay [NON_GATING] sidebar."""
    field = brief.get("field_final_call") or {}
    if not field and not brief.get("today_action"):
        return
    attach = _ko_attach_mode(field.get("attach_mode"))
    posture = _ko_operator_posture(field.get("operator_posture"))
    promo = _ko_promotion_decision(brief.get("promotion_decision") or brief.get("system_status") or "—")
    lines.extend(
        [
            "",
            "▸ 실물·최종판단 [정량]",
            f"  부착 {attach} · 자세 {posture} · 승격 {promo}",
            "  3렌즈 보조(비게이팅) — 최종판 미반영",
        ]
    )


def _morning_kospi_only_window() -> bool:
    """06:00–10:59 KST — single Korean prophecy briefing policy."""
    if not _truthy("MKM_TELEGRAM_MORNING_KOSPI_ONLY", default=True):
        return False
    return 6 <= datetime.now(KST).hour < 11


def _kospi_only_digest() -> bool:
    """Morning prophecy body: KOSPI leg only (no BTC/MULTI hit-rate or non-KOSPI hypothesis)."""
    return _truthy("MKM_TELEGRAM_MORNING_KOSPI_ONLY", default=True)


def build_digest_prophecy_slim(workspace: Path) -> str:
    """장전 코스피 슬림(~10줄) — 일운·4AI·미션C·채널 상세 제외."""
    art = workspace / "docs" / "final" / "artifacts"
    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    dual_leg = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    hypo = _read_json(art / "btrack_hypothesis_prophecy_latest.json")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M") + " 한국시"
    action = _ko_market_action(brief.get("today_action"))
    conf = brief.get("confidence_0_100")
    session_ko = brief.get("market_session_ko") or ""
    kospi_n, kospi_hr = _leg_metrics(dual_leg, "kospi")
    if brief.get("dual_leg_kospi_n_evaluated") is not None:
        kospi_n = brief.get("dual_leg_kospi_n_evaluated")
    if brief.get("dual_leg_kospi_hit_rate") is not None:
        kospi_hr = brief.get("dual_leg_kospi_hit_rate")

    pred = hypo.get("prediction") or {}
    hypo_inst = str(pred.get("instrument") or "—").upper()
    if hypo_inst == "KOSPI":
        hypo_inst = "코스피"
    elif hypo_inst in {"BTC", "MULTI"}:
        hypo_inst = ""
    hypo_dir = _ko_direction(pred.get("direction"))
    hypo_conf = pred.get("confidence")

    line_action = f"▸ 오늘: {action}" + (f" · 확신 {conf}/100" if conf is not None else "")
    if session_ko:
        line_action += f" · {session_ko}"

    lines: List[str] = [
        f"MKM 장전 코스피 · {now_kst}",
        "[가설] B트랙 · 실매매·Track A 연동 없음",
        "",
        line_action,
        f"▸ 코스피 적중: {_fmt_pct(kospi_hr)} (n={kospi_n})",
    ]
    if hypo_inst == "코스피":
        conf_s = f" · 신뢰 {float(hypo_conf):.2f}" if hypo_conf is not None else ""
        lines.append(f"▸ 가설: 코스피 · 방향 {hypo_dir}{conf_s}")

    return _sanitize_telegram_ko(_truncate_telegram("\n".join(lines)))


def build_digest_prophecy(workspace: Path) -> str:
    """장전 예언 브리핑만(한글) — 일운·RAG·VPS·패널·R-IBL·운영 잡음 제외."""
    if _prophecy_slim_enabled():
        return build_digest_prophecy_slim(workspace)
    art = workspace / "docs" / "final" / "artifacts"

    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    dual_leg = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    hypo = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    hit = _read_json(art / "prophecy_hit_rate_eval_latest.json")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M") + " 한국시"
    brief_ts = _fmt_kst_from_utc(brief.get("generated_at_utc") or dual_leg.get("generated_at_utc"))

    action = _ko_market_action(brief.get("today_action"))
    conf = brief.get("confidence_0_100")
    session_ko = brief.get("market_session_ko") or ""
    kospi_n, kospi_hr = _leg_metrics(dual_leg, "kospi")
    if brief.get("dual_leg_kospi_n_evaluated") is not None:
        kospi_n = brief.get("dual_leg_kospi_n_evaluated")
    if brief.get("dual_leg_kospi_hit_rate") is not None:
        kospi_hr = brief.get("dual_leg_kospi_hit_rate")
    btc_n, btc_hr = _leg_metrics(dual_leg, "btc")
    pooled = hit.get("metrics") or {}

    pred = hypo.get("prediction") or {}
    hypo_inst = str(pred.get("instrument") or "—").upper()
    if hypo_inst == "KOSPI":
        hypo_inst = "코스피"
    elif hypo_inst == "BTC":
        hypo_inst = "비트코인"
    elif hypo_inst == "MULTI":
        hypo_inst = "멀티(코스피·비트코인)"
    hypo_dir = _ko_direction(pred.get("direction"))
    hypo_conf = pred.get("confidence")
    rm = hypo.get("runtime_meta") if isinstance(hypo.get("runtime_meta"), dict) else {}
    lv = rm.get("lens_values") if isinstance(rm.get("lens_values"), dict) else {}
    overlay = ((rm.get("price_meta") or {}).get("kospi_overnight_overlay") or {})
    if not isinstance(overlay, dict):
        overlay = {}

    lines: List[str] = [
        f"MKM 장전 예언 브리핑 · {now_kst}",
        f"근거 시각: {brief_ts}",
        "[가설] B트랙 · 실매매·압축A 자동 연동 없음",
        "",
        f"▸ 오늘 장전: {action}" + (f" · 확신 {conf}/100" if conf is not None else ""),
    ]
    if session_ko:
        lines.append(f"  세션: {session_ko}")
    _append_field_final_call_telegram(lines, brief)
    kospi_only = _kospi_only_digest()
    hit_lines = [
        "",
        "▸ 적중률(관측)",
        f"  코스피: {_fmt_pct(kospi_hr)} (표본 {kospi_n})",
    ]
    if not kospi_only:
        hit_lines.extend(
            [
                f"  비트코인: {_fmt_pct(btc_hr)} (표본 {btc_n})",
                f"  통합: {_fmt_pct(pooled.get('price_directional_hit_rate'))} (표본 {pooled.get('n_evaluated')})",
            ]
        )
    lines.extend(hit_lines)
    _append_mission_c_shadow_telegram(lines, workspace)
    if not kospi_only or hypo_inst == "코스피":
        lines.extend(
            [
                "",
                "▸ B트랙 가격 가설",
                f"  {hypo_inst} · 방향 {hypo_dir}"
                + (f" · 신뢰 {float(hypo_conf):.2f}" if hypo_conf is not None else ""),
            ]
        )
    if overlay.get("applied"):
        us_s = overlay.get("us_overnight_score")
        dom_s = overlay.get("domestic_price_score")
        blend_s = overlay.get("price_score_after_blend")
        tilt = _ko_composite_tilt(overlay.get("composite_tilt"))
        lines.extend(
            [
                "",
                "▸ 레짐·오버나이트 [가설]",
                f"  {tilt} · 미국 야간 {us_s} · 국내 {dom_s} → 혼합 {blend_s}",
            ]
        )
    price_s = lv.get("price", {}).get("score")
    news_s = lv.get("news", {}).get("score")
    macro_s = lv.get("macro", {}).get("score")
    if price_s is not None or news_s is not None:
        lines.extend(
            [
                "",
                "▸ B트랙 렌즈 스냅샷",
                f"  가격 {_fmt_lens_score(price_s)} · 뉴스 {_fmt_lens_score(news_s)} · 거시 {_fmt_lens_score(macro_s)}",
            ]
        )
        for lens_key, lens_label in (("myeongni", "명리"), ("sasang", "사상"), ("logos", "성경")):
            lv_lens = lv.get(lens_key) or {}
            if lv_lens.get("score") is not None or lv_lens.get("direction"):
                lines.append(
                    f"  {lens_label} 방향 {_ko_direction(lv_lens.get('direction'))}"
                    f" · 점수 {lv_lens.get('score')}"
                )

    cal_kst = datetime.now(KST).strftime("%Y-%m-%d")
    _append_kospi_date_detail(lines, workspace, cal_kst, brief=brief, hypo=hypo)

    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    fortune = _read_json(fortune_path) if fortune_path.is_file() else {}
    include_fortune = _truthy("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", default=True)
    if include_fortune:
        lines.extend(["", "▸ 지휘관 사주·명리·일운"])
        _append_fortune_detail(lines, fortune, depth="full")
    else:
        lines.extend(["", "▸ 지휘관 일운 요약"])
        _append_fortune_detail(lines, fortune, depth="compact")

    if _truthy("MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL", default=False):
        registry = _read_json(workspace / "reports" / "research_morning_prediction_registry_latest.json")
        if registry.get("schema") == "research_morning_prediction_registry_v1":
            by_lens = registry.get("predictions_by_lens") or {}
            lens_summary = " · ".join(f"{k}={v}" for k, v in sorted(by_lens.items()))
            lines.extend(
                [
                    "",
                    f"▸ 연구봉인: {registry.get('n_predictions')}건 · 봉인={registry.get('seal_id')}",
                    f"  렌즈 {lens_summary or '—'}",
                ]
            )
            for p in (registry.get("predictions") or [])[:2]:
                if isinstance(p, dict) and p.get("claim_ko"):
                    lines.append(f"  · {str(p.get('claim_ko'))[:120]}")

    return _sanitize_telegram_ko(_truncate_telegram("\n".join(lines)))


def build_digest_minimal(workspace: Path) -> str:
    art = workspace / "docs" / "final" / "artifacts"
    reports = workspace / "reports"

    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    dual_leg = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    hit = _read_json(art / "prophecy_hit_rate_eval_latest.json")
    panel = _read_json(reports / "prophecy_panel_24h_alerts_latest.json")
    live = _read_json(workspace / "live_sync" / "incoming" / "daemon_alive_check.json")

    kospi_action = brief.get("today_action") or "—"
    kospi_conf = brief.get("confidence_0_100")
    kospi_n = brief.get("dual_leg_kospi_n_evaluated")
    if kospi_n is None:
        kospi_n = _leg_metrics(dual_leg, "kospi")[0]
    kospi_hr = brief.get("dual_leg_kospi_hit_rate")
    if kospi_hr is None:
        kospi_hr = _leg_metrics(dual_leg, "kospi")[1]
    metrics = hit.get("metrics") or {}
    hit_rate = metrics.get("price_directional_hit_rate")
    n_eval = metrics.get("n_evaluated")
    panel_ok = panel.get("overall_passed")
    panel_line = "OK" if panel_ok is True else ("FAIL" if panel_ok is False else "—")

    live_line = "—"
    if live:
        alive = live.get("alive")
        ts = live.get("checked_at_utc") or live.get("ts_utc") or ""
        live_line = f"{'online' if alive else 'stale'} ({ts[:19] if ts else 'no-ts'})"

    lines = [
        "MKM 핵심 (장전/일일)",
        f"• KOSPI 브리프: {kospi_action} (신뢰 {kospi_conf}/100) [internal_only]",
        f"• KOSPI 적중(B-track): {_fmt_pct(kospi_hr)} n={kospi_n} [HYPO·관측]",
        f"• BTC·통합 적중: {_fmt_pct(hit_rate)} n={n_eval} [HYPO·관측]",
        f"• 패널 24h: {panel_line}",
        f"• VPS heartbeat: {live_line}",
        "—",
        "실매매 자동 트리거 아님. 체결 알림은 VPS trade_only 정책.",
    ]
    return "\n".join(lines)


def build_digest_advanced(workspace: Path) -> str:
    """Unified advanced briefing (fortune + world + predictions + market obs)."""
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    try:
        sys.path.insert(0, str(workspace / "scripts"))
        from build_commander_telegram_advanced_briefing_v1 import (  # noqa: WPS433
            archive_morning_briefing,
            build_advanced_briefing_doc,
            build_telegram_text,
        )

        doc = build_advanced_briefing_doc(workspace, fortune_path=fortune_path)
        archive_morning_briefing(doc, workspace)
        out_path = workspace / "reports" / "commander_advanced_briefing_latest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return build_telegram_text(doc)
    except Exception as exc:  # noqa: BLE001
        lines = [
            f"📊 MKM 장전 브리핑 · {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}",
            f"(advanced builder fallback: {str(exc)[:120]})",
        ]
        _append_personal_fortune(workspace, lines)
        text = "\n".join(lines)
        if len(text) > TELEGRAM_MAX_LEN:
            return text[: TELEGRAM_MAX_LEN - 20] + "\n…(truncated)"
        return text


def build_digest_evening_review(workspace: Path) -> str:
    """Evening scorecard Telegram — scores R-IBL morning seal predictions."""
    try:
        sys.path.insert(0, str(workspace / "scripts"))
        from score_research_evening_predictions_v1 import (  # noqa: WPS433
            build_evening_telegram,
            resolve_research_seal,
            score_research_evening,
        )
        from run_commander_briefing_evolution_v1 import run_evolution  # noqa: WPS433

        cal = datetime.now(KST).strftime("%Y-%m-%d")
        seal = resolve_research_seal(cal)
        score_path = workspace / "reports" / "evening_multi_lens_score_v1.json"
        score: dict = {}
        if score_path.is_file():
            score = json.loads(score_path.read_text(encoding="utf-8-sig"))
        if score.get("schema") == "evening_multi_lens_score_v1" and score.get("calendar_kst") == cal:
            pass
        elif seal.is_file():
            include_bn = os.getenv("MKM_EVENING_INCLUDE_BINANCE_SHADOW", "1").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
            score = score_research_evening(
                seal,
                workspace=workspace,
                include_binance_shadow=include_bn,
            )
            score_path.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            return f"🌙 MKM 저녁 채점 · {cal}\nR-IBL seal 없음 ({seal.name})"
        evo = run_evolution(dry_run=True)
        evo_path = workspace / "reports" / "commander_briefing_evolution_latest.json"
        evo_path.write_text(json.dumps(evo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        text = build_evening_telegram(score, evolution=evo)
        props = len(evo.get("proposals") or [])
        if props and "▸ 진화 제안" not in text:
            avg = evo.get("avg_soft_hit_rate")
            avg_s = f"{float(avg)*100:.1f}%" if avg is not None else "n/a"
            text += f"\n\n▸ 자율진화(드라이런): 제안 {props}건 · 평균소프트={avg_s}"
        if len(text) > TELEGRAM_MAX_LEN:
            return text[: TELEGRAM_MAX_LEN - 20] + "\n…(잘림)"
        return text
    except Exception as exc:  # noqa: BLE001
        return f"🌙 MKM 저녁 채점 오류: {str(exc)[:200]}"


def _resolve_style(cli_style: Optional[str]) -> str:
    if cli_style:
        return cli_style.strip().lower()
    env = os.getenv("MKM_TELEGRAM_DIGEST_STYLE", "prophecy").strip().lower()
    return env if env in {"minimal", "advanced", "prophecy", "personal", "afternoon", "evening_review"} else "prophecy"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Send even if MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED is off")
    ap.add_argument(
        "--scheduled-morning",
        action="store_true",
        help="08:28 task: force enable + --style prophecy (Korean KOSPI briefing only)",
    )
    ap.add_argument(
        "--scheduled-afternoon",
        action="store_true",
        help="18:00 task: force enable + --style afternoon (Korean fortune + KOSPI)",
    )
    ap.add_argument(
        "--allow-legacy-style",
        action="store_true",
        help="Allow advanced/personal/minimal during 06–11 KST (default blocked)",
    )
    ap.add_argument(
        "--style",
        choices=("minimal", "advanced", "prophecy", "personal", "afternoon", "evening_review"),
        default=None,
        help="Digest layout (default: env MKM_TELEGRAM_DIGEST_STYLE or prophecy=장전 한글)",
    )
    args = ap.parse_args()
    _load_dotenv()

    if args.scheduled_morning:
        os.environ["MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED"] = "1"
        os.environ.setdefault("MKM_TELEGRAM_DIGEST_STYLE", "prophecy")
        os.environ.setdefault("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1")
        os.environ.setdefault("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "0")
        os.environ.setdefault("MKM_TELEGRAM_PROPHECY_SLIM", "1")
        os.environ.setdefault("MKM_TELEGRAM_PROPHECY_INCLUDE_MISSION_C_SHADOW", "0")
        for _k in (
            "MKM_TELEGRAM_PROPHECY_INCLUDE_RIBL",
            "MKM_TELEGRAM_PROPHECY_INCLUDE_OPS_CONTEXT",
            "MKM_TELEGRAM_PROPHECY_INCLUDE_DEV_COACH",
            "MKM_TELEGRAM_PROPHECY_INCLUDE_TRUST_POINTER",
        ):
            if not os.getenv(_k, "").strip():
                os.environ[_k] = "0"
        args.force = True
        if args.style is None:
            args.style = "prophecy"

    if args.scheduled_afternoon:
        os.environ["MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED"] = "1"
        os.environ["MKM_TELEGRAM_DIGEST_STYLE"] = "afternoon"
        args.force = True
        if args.style is None:
            args.style = "afternoon"

    if not args.force and not _truthy("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", default=False):
        print("SKIP: MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED not set")
        return 0

    style = _resolve_style(args.style)
    if style == "evening_review" and not _truthy("MKM_TELEGRAM_EVENING_DIGEST_ENABLED", default=False):
        print("SKIP: MKM_TELEGRAM_EVENING_DIGEST_ENABLED not set (evening_review blocked)")
        return 0
    if style in {"advanced", "minimal", "personal"} and not _truthy(
        "MKM_TELEGRAM_LEGACY_DIGEST_ENABLED", default=False
    ):
        print(f"SKIP: legacy style={style} blocked (set MKM_TELEGRAM_LEGACY_DIGEST_ENABLED=1 to override)")
        return 0
    if (
        not args.allow_legacy_style
        and style != "prophecy"
        and _morning_kospi_only_window()
    ):
        print(
            f"SKIP: morning KST (06–11) allows Korean prophecy only; blocked style={style}. "
            "Use --style prophecy or --allow-legacy-style.",
            file=sys.stderr,
        )
        return 0
    text = build_digest(args.workspace_root.resolve(), style=style)
    print(text)
    if args.dry_run:
        preview = args.workspace_root / "reports" / "telegram_daily_wiring_digest_preview_latest.txt"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {preview}")
        print("DRY RUN: not sent")
        return 0

    token = _resolve_secret("TELEGRAM_BOT_TOKEN")
    chat = _resolve_secret("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print(
            "SKIP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing "
            "(set User env, DPAPI via Invoke-EncryptedSecretStore.ps1 -Action set, or .env)",
            file=sys.stderr,
        )
        return 0

    ok, msg = _send_telegram(token, chat, text)
    out = {
        "schema": "telegram_ops_digest_v1",
        "style": style,
        "sent_at_utc": _utc_now(),
        "ok": ok,
        "result": msg,
        "char_count": len(text),
    }
    out_path = args.workspace_root / "reports" / "telegram_minimal_ops_digest_latest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
