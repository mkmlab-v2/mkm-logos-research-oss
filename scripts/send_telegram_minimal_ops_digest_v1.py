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
            return "n/a"
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return "n/a"


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
    )
    out = line
    for old, new in repl:
        out = out.replace(old, new)
    return out


def build_digest_personal(workspace: Path) -> str:
    """지휘관 개인 일운(명리·4AI·라이프)만 — 예언/KOSPI/BTC/VPS 블록 없음."""
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
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


def build_digest(workspace: Path, *, style: str = "minimal") -> str:
    if style == "personal":
        return build_digest_personal(workspace)
    if style == "prophecy":
        return build_digest_prophecy(workspace)
    if style == "advanced":
        return build_digest_advanced(workspace)
    if style == "evening_review":
        return build_digest_evening_review(workspace)
    return build_digest_minimal(workspace)


def _append_personal_fortune(workspace: Path, lines: List[str]) -> None:
    if not _truthy("MKM_TELEGRAM_INCLUDE_PERSONAL_FORTUNE", default=True):
        return
    fortune_path = workspace / "reports" / "commander_daily_fortune_latest.json"
    if not fortune_path.is_file():
        return
    doc = _read_json(fortune_path)
    schema = doc.get("schema") or ""
    if schema not in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1"):
        return
    for ln in doc.get("telegram_append_lines") or []:
        if ln:
            lines.append(ln)


def build_digest_prophecy(workspace: Path) -> str:
    """장전 예언 브리핑만 — Logos/Track C/VPS/패널·체크리스트 등 운영 잡음 제외."""
    art = workspace / "docs" / "final" / "artifacts"

    brief = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")
    dual_leg = _read_json(art / "trackc_prophecy_dual_leg_brief_latest.json")
    hypo = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    hit = _read_json(art / "prophecy_hit_rate_eval_latest.json")

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    brief_ts = _fmt_kst_from_utc(brief.get("generated_at_utc") or dual_leg.get("generated_at_utc"))

    action = brief.get("today_action") or "—"
    conf = brief.get("confidence_0_100")
    kospi_n, kospi_hr = _leg_metrics(dual_leg, "kospi")
    if brief.get("dual_leg_kospi_n_evaluated") is not None:
        kospi_n = brief.get("dual_leg_kospi_n_evaluated")
    if brief.get("dual_leg_kospi_hit_rate") is not None:
        kospi_hr = brief.get("dual_leg_kospi_hit_rate")
    btc_n, btc_hr = _leg_metrics(dual_leg, "btc")
    pooled = hit.get("metrics") or {}

    pred = hypo.get("prediction") or {}
    hypo_inst = pred.get("instrument") or "—"
    hypo_dir = pred.get("direction") or "—"
    hypo_conf = pred.get("confidence")

    lines: List[str] = [
        f"MKM 예언 브리핑 · {now_kst}",
        f"근거: {brief_ts}",
        "",
        f"▸ 오늘: {action} | 확신 {conf}/100",
        "  B-track [HYPO] · 실매매 자동 트리거 아님",
        "",
        "▸ 적중(관측)",
        f"  KOSPI: {_fmt_pct(kospi_hr)} (n={kospi_n}) · BTC: {_fmt_pct(btc_hr)} (n={btc_n})",
        f"  통합: {_fmt_pct(pooled.get('price_directional_hit_rate'))} (n={pooled.get('n_evaluated')})",
        "",
        f"▸ 가설: {hypo_inst} {hypo_dir}" + (f" (conf {hypo_conf})" if hypo_conf is not None else ""),
    ]
    _append_personal_fortune(workspace, lines)
    text = "\n".join(lines)
    if len(text) > TELEGRAM_MAX_LEN:
        return text[: TELEGRAM_MAX_LEN - 20] + "\n…(truncated)"
    return text


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
    """Evening scorecard Telegram — scores morning briefing_id predictions."""
    try:
        sys.path.insert(0, str(workspace / "scripts"))
        from score_commander_evening_briefing_v1 import (  # noqa: WPS433
            build_evening_telegram,
            resolve_archive,
            score_evening_briefing,
        )
        from run_commander_briefing_evolution_v1 import run_evolution  # noqa: WPS433

        cal = datetime.now(KST).strftime("%Y-%m-%d")
        arch = resolve_archive(cal)
        if not arch.is_file():
            return f"🌙 MKM 저녁 채점 · {cal}\n아침 브리핑 아카이브 없음 ({arch.name})"
        score = score_evening_briefing(arch)
        out = workspace / "reports" / "commander_evening_briefing_score_latest.json"
        out.write_text(json.dumps(score, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evo = run_evolution(dry_run=True)
        evo_path = workspace / "reports" / "commander_briefing_evolution_latest.json"
        evo_path.write_text(json.dumps(evo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        text = build_evening_telegram(score)
        props = len(evo.get("proposals") or [])
        text += f"\n\n▸ 자율진화(dry-run): 제안 {props}건 · avg_soft={evo.get('avg_soft_hit_rate')}"
        if len(text) > TELEGRAM_MAX_LEN:
            return text[: TELEGRAM_MAX_LEN - 20] + "\n…(truncated)"
        return text
    except Exception as exc:  # noqa: BLE001
        return f"🌙 MKM 저녁 채점 오류: {str(exc)[:200]}"


def _resolve_style(cli_style: Optional[str]) -> str:
    if cli_style:
        return cli_style.strip().lower()
    env = os.getenv("MKM_TELEGRAM_DIGEST_STYLE", "personal").strip().lower()
    return env if env in {"minimal", "advanced", "prophecy", "personal", "evening_review"} else "personal"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Send even if MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED is off")
    ap.add_argument(
        "--style",
        choices=("minimal", "advanced", "prophecy", "personal", "evening_review"),
        default=None,
        help="Digest layout (default: env MKM_TELEGRAM_DIGEST_STYLE or personal=일운만)",
    )
    args = ap.parse_args()
    _load_dotenv()

    if not args.force and not _truthy("MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED", default=False):
        print("SKIP: MKM_TELEGRAM_MINIMAL_DIGEST_ENABLED not set")
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

    style = _resolve_style(args.style)
    text = build_digest(args.workspace_root.resolve(), style=style)
    print(text)
    if args.dry_run:
        print("DRY RUN: not sent")
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
