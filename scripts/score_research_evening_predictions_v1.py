#!/usr/bin/env python3
"""R-IBL Phase 2 — score morning research seal vs evening market close [HYPO][research_only].

SSOT input: reports/briefing_log/{YYYY-MM-DD}_research_seal_v1.json
Price data: offline YFinance CSV refresh (same rail as daily prophecy bundle).
No Track A / live trading / go_no_go auto-merge.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
KST = ZoneInfo("Asia/Seoul")
BRIEFING_LOG = ROOT / "reports" / "briefing_log"
DEFAULT_OUT = ROOT / "reports" / "evening_multi_lens_score_v1.json"
SCHEMA = "evening_multi_lens_score_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_research_seal(date_kst: str) -> Path:
    return BRIEFING_LOG / f"{date_kst}_research_seal_v1.json"


def resolve_morning_briefing_archive(date_kst: str, *, workspace: Path = ROOT) -> Path:
    return workspace / "reports" / "briefing_log" / f"{date_kst}_morning_briefing_v1.json"


def _resolve_morning_market_seal(
    calendar_kst: str,
    *,
    workspace: Path = ROOT,
    envelope: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Morning BTC anchor for 12h window — same sources as commander evening score."""
    env = envelope or {}
    if isinstance(env.get("market_seal"), dict):
        return env["market_seal"], "research_seal_envelope.market_seal"

    reg = env.get("registry") if env.get("schema") == "research_morning_seal_archive_v1" else env
    if isinstance(reg, dict) and isinstance(reg.get("market_seal"), dict):
        return reg["market_seal"], "research_seal_registry.market_seal"

    arch = resolve_morning_briefing_archive(calendar_kst, workspace=workspace)
    if arch.is_file():
        doc = _read_json(arch)
        briefing = doc.get("briefing") or doc
        ms = briefing.get("market_seal")
        if isinstance(ms, dict):
            return ms, f"briefing_log/{arch.name}"

    latest = workspace / "reports" / "commander_morning_briefing_latest.json"
    if latest.is_file():
        doc = _read_json(latest)
        if str(doc.get("calendar_kst") or (doc.get("briefing") or {}).get("calendar_kst")) == calendar_kst:
            briefing = doc.get("briefing") or doc
            ms = briefing.get("market_seal")
            if isinstance(ms, dict):
                return ms, "commander_morning_briefing_latest.json"

    return None, "none"


def load_registry_from_seal(seal_path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    env = _read_json(seal_path)
    if env.get("schema") == "research_morning_seal_archive_v1":
        reg = env.get("registry") or {}
        return reg, env
    if env.get("schema") == "research_morning_prediction_registry_v1":
        return env, {"schema": "research_morning_seal_archive_v1", "registry": env}
    return {}, env


def _price_axis_outcome(
    *,
    direction_proxy: str,
    market_direction: str,
    kind: str,
) -> Tuple[str, str]:
    """Map directional claims to HIT / FAIL / NEUTRAL_DRAW."""
    if market_direction in ("insufficient_data", "market_closed"):
        return "insufficient_data", "마감 데이터 없음"

    proxy = str(direction_proxy or "").lower()
    mdir = str(market_direction or "").lower()

    if kind == "kospi_morning_action":
        act = proxy.upper()
        if act in ("WATCH", "HOLD", "CAUTION", "REDUCE") and mdir == "down":
            return "HIT", "경계 액션 + 하락일"
        if act in ("GO", "TILT_UP", "BUY") and mdir == "up":
            return "HIT", "우위 액션 + 상승일"
        if act in ("WATCH", "HOLD") and mdir == "flat":
            return "NEUTRAL_DRAW", "횡보·관측"
        return "NEUTRAL_DRAW", "액션 vs 종가 방향 느슨 대조"

    bull = proxy in ("bull", "up", "go", "tilt_up", "buy")
    bear = proxy in ("bear", "down", "reduce", "caution")
    neutral = proxy in ("neutral", "flat", "watch", "hold")

    if bull and mdir == "up":
        return "HIT", "상승 방향 일치"
    if bear and mdir == "down":
        return "HIT", "하락 방향 일치"
    if neutral and mdir == "flat":
        return "NEUTRAL_DRAW", "중립·횡보"
    if neutral:
        return "NEUTRAL_DRAW", "중립 라벨 — 방향 단정 없음"
    return "FAIL", "방향 불일치"


def _resolve_asset_for_pred(pred: Dict[str, Any], assets: Dict[str, Any]) -> Tuple[str, str]:
    against = str(pred.get("score_against") or "")
    inst = against.lower()
    if "btc" in inst and "kospi" not in inst:
        b = assets.get("btc") or {}
        return "btc", str(b.get("direction") or "insufficient_data")
    if "btc" in inst and "kospi" in inst:
        k = assets.get("kospi") or {}
        b = assets.get("btc") or {}
        kd = str(k.get("direction") or "insufficient_data")
        bd = str(b.get("direction") or "insufficient_data")
        if kd == bd and kd not in ("insufficient_data", "market_closed"):
            return "dual_kospi_btc", kd
        return "dual_kospi_btc", kd if kd not in ("insufficient_data", "market_closed") else bd
    k = assets.get("kospi") or {}
    return "kospi", str(k.get("direction") or "insufficient_data")


def _graphrag_replay_passes(replay: Dict[str, Any], *, replay_path: Path, workspace: Path) -> bool:
    """Router v1.3 artifacts omit top-level pass; infer from paths or batch summary."""
    if replay.get("pass") is True:
        return True
    if replay.get("pass") is False:
        return False
    paths = replay.get("paths") or []
    if paths:
        return True
    if int(replay.get("bridges_matched") or 0) > 0:
        return True
    summary = _read_json(workspace / "reports" / "subgraph_router_replay_summary_latest.json")
    rel = str(replay_path).replace("\\", "/")
    for row in summary.get("rows") or []:
        if not isinstance(row, dict):
            continue
        out_json = str(row.get("out_json") or "").replace("\\", "/")
        if out_json and (out_json in rel or rel.endswith(out_json.split("/")[-1])):
            return bool(row.get("pass"))
    return False


def _score_logos_graphrag(pred: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    ev = str(pred.get("evidence_path") or "")
    replay_path = workspace / ev if ev else Path()
    replay = _read_json(replay_path) if replay_path.is_file() else {}
    passed = _graphrag_replay_passes(replay, replay_path=replay_path, workspace=workspace)
    if passed:
        outcome, note = "HIT", "아침 subgraph replay pass — 구조적 경로 적중(가격 비단정)"
    elif not replay:
        outcome, note = "FAIL", "evidence 누락"
    else:
        outcome, note = "FAIL", "replay 경로·요약 모두 pass=false"
    return {
        "prediction_id": pred.get("prediction_id"),
        "lens": pred.get("lens"),
        "kind": pred.get("kind"),
        "price_axis": "N/A",
        "outcome": outcome,
        "note": note,
        "branch_id": _branch_id_from_pred(pred),
    }


def _score_logos_gold_eval(pred: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    ev = str(pred.get("evidence_path") or "")
    gold_path = workspace / ev if ev else Path()
    gold = _read_json(gold_path) if gold_path.is_file() else {}
    ok = bool((gold.get("summary") or {}).get("gold_required_all_pass"))
    outcome = "HIT" if ok else "FAIL"
    note = "gold_required_all_pass 유지" if ok else "gold eval 미통과 또는 파일 없음"
    return {
        "prediction_id": pred.get("prediction_id"),
        "lens": pred.get("lens"),
        "kind": pred.get("kind"),
        "price_axis": "N/A",
        "outcome": outcome,
        "note": note,
        "branch_id": _branch_id_from_pred(pred),
    }


def _branch_id_from_pred(pred: Dict[str, Any]) -> Optional[str]:
    pid = str(pred.get("prediction_id") or "")
    if "_myeongni_branch_" in pid:
        return pid.split("_myeongni_branch_", 1)[-1]
    return None


def _score_directional(
    pred: Dict[str, Any],
    *,
    assets: Dict[str, Any],
) -> Dict[str, Any]:
    asset, mdir = _resolve_asset_for_pred(pred, assets)
    kind = str(pred.get("kind") or "")
    proxy = str(pred.get("direction_proxy") or "")
    price_axis, note = _price_axis_outcome(
        direction_proxy=proxy,
        market_direction=mdir,
        kind=kind,
    )
    legacy = "aligned" if price_axis == "HIT" else ("reject" if price_axis == "FAIL" else "partial")
    if price_axis == "insufficient_data":
        legacy = "insufficient_data"
    if kind in ("narrative_hypothesis", "hypothesis_stream_branch") and mdir == "down":
        if price_axis == "NEUTRAL_DRAW":
            legacy = "partial"
            note = "행동·내러티브 가설 — 하락일 관측(느슨)"
    return {
        "prediction_id": pred.get("prediction_id"),
        "lens": pred.get("lens"),
        "kind": kind,
        "price_axis": price_axis,
        "outcome": legacy,
        "note": note,
        "market_direction": mdir,
        "asset": asset,
        "branch_id": _branch_id_from_pred(pred),
    }


def _score_reference_only(pred: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "prediction_id": pred.get("prediction_id"),
        "lens": pred.get("lens"),
        "kind": pred.get("kind"),
        "price_axis": "REFERENCE_ONLY",
        "outcome": "neutral",
        "note": "베이스라인·관측 통계 — 일일 HIT/FAIL 채점 제외",
        "branch_id": _branch_id_from_pred(pred),
    }


def score_prediction(
    pred: Dict[str, Any],
    *,
    assets: Dict[str, Any],
    workspace: Path,
) -> Dict[str, Any]:
    kind = str(pred.get("kind") or "")
    if kind == "graphrag_path_hit":
        return _score_logos_graphrag(pred, workspace)
    if kind == "graphrag_gold_eval":
        return _score_logos_gold_eval(pred, workspace)
    if kind == "shadow_panel_baseline":
        return _score_reference_only(pred)
    return _score_directional(pred, assets=assets)


def _aggregate_by_lens(scored: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    agg: Dict[str, Dict[str, Any]] = {}
    for s in scored:
        lens = str(s.get("lens") or "unknown")
        bucket = agg.setdefault(lens, {"n": 0, "HIT": 0, "FAIL": 0, "NEUTRAL_DRAW": 0, "other": 0})
        bucket["n"] += 1
        pa = s.get("price_axis")
        if pa in ("HIT", "FAIL", "NEUTRAL_DRAW"):
            bucket[str(pa)] += 1
        else:
            bucket["other"] += 1
    for lens, bucket in agg.items():
        scorable = bucket["HIT"] + bucket["FAIL"] + bucket["NEUTRAL_DRAW"]
        bucket["soft_hit_rate"] = round(
            (bucket["HIT"] + 0.5 * bucket["NEUTRAL_DRAW"]) / scorable, 4
        ) if scorable else None
        agg[lens] = bucket
    return agg


def _aggregate_by_kind(scored: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    agg: Dict[str, Dict[str, int]] = {}
    for s in scored:
        kind = str(s.get("kind") or "unknown")
        o = str(s.get("price_axis") if s.get("price_axis") in ("HIT", "FAIL", "NEUTRAL_DRAW") else s.get("outcome"))
        agg.setdefault(kind, {})
        agg[kind][o] = agg[kind].get(o, 0) + 1
    return agg


def _aggregate_by_branch(scored: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    agg: Dict[str, Dict[str, int]] = {}
    for s in scored:
        bid = s.get("branch_id")
        if not bid:
            continue
        agg.setdefault(str(bid), {})
        o = str(s.get("outcome") or "neutral")
        agg[str(bid)][o] = agg[str(bid)].get(o, 0) + 1
    return agg


def score_research_evening(
    seal_path: Path,
    *,
    workspace: Path = ROOT,
    include_binance_shadow: bool = False,
) -> Dict[str, Any]:
    from scripts.multi_asset_market_adapter_v1 import build_evening_asset_panel  # noqa: WPS433

    registry, envelope = load_registry_from_seal(seal_path)
    if registry.get("schema") != "research_morning_prediction_registry_v1":
        raise ValueError(f"invalid registry in seal: {seal_path}")

    cal = str(registry.get("calendar_kst") or envelope.get("calendar_kst") or "")
    morning_seal, morning_seal_source = _resolve_morning_market_seal(
        cal, workspace=workspace, envelope=envelope
    )
    assets = build_evening_asset_panel(cal, morning_seal=morning_seal)

    binance_shadow: Dict[str, Any] = {"enabled": False}
    if include_binance_shadow:
        from scripts.fetch_btc_binance_24h_shadow_v1 import (  # noqa: WPS433
            dual_leg_agreement,
            fetch_binance_btc_shadow,
        )

        binance_shadow = fetch_binance_btc_shadow(calendar_kst=cal)
        binance_shadow["enabled"] = True
        yf_btc_dir = str((assets.get("btc") or {}).get("direction") or "")
        bn_dir = str((binance_shadow.get("latest_daily") or {}).get("direction") or "")
        binance_shadow["dual_leg_agreement"] = dual_leg_agreement(yf_btc_dir, bn_dir)

    scored: List[Dict[str, Any]] = []
    for pred in registry.get("predictions") or []:
        if isinstance(pred, dict):
            row = score_prediction(pred, assets=assets, workspace=workspace)
            if include_binance_shadow and binance_shadow.get("ok"):
                against = str(pred.get("score_against") or "").lower()
                if "btc" in against and binance_shadow.get("latest_daily"):
                    bn_dir = str(binance_shadow["latest_daily"].get("direction") or "")
                    pa, note = _price_axis_outcome(
                        direction_proxy=str(pred.get("direction_proxy") or ""),
                        market_direction=bn_dir,
                        kind=str(pred.get("kind") or ""),
                    )
                    row["price_axis_binance_shadow"] = pa
                    row["binance_shadow_note"] = note
            scored.append(row)

    by_lens = _aggregate_by_lens(scored)
    price_hits = sum(1 for s in scored if s.get("price_axis") == "HIT")
    price_fails = sum(1 for s in scored if s.get("price_axis") == "FAIL")
    price_neutral = sum(1 for s in scored if s.get("price_axis") == "NEUTRAL_DRAW")
    price_scorable = price_hits + price_fails + price_neutral
    price_soft = (
        (price_hits + 0.5 * price_neutral) / price_scorable if price_scorable else None
    )

    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_a_auto_merge_forbidden": True,
        "live_trading_trigger_forbidden": True,
        "scored_at_utc": _utc_now(),
        "calendar_kst": cal,
        "seal_id": registry.get("seal_id"),
        "seal_path": str(seal_path),
        "data_source": {
            "primary": "yfinance_csv_offline",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "btc_evening_window": "08:10-20:30_snapshot_via_yfinance",
            "morning_market_seal_source": morning_seal_source,
            "morning_btc_seal_price": ((morning_seal or {}).get("btc_usd") or {}).get("price"),
            "binance_sidecar": binance_shadow if include_binance_shadow else "not_enabled",
        },
        "multi_asset": assets,
        "prediction_scores": scored,
        "stats_by_lens": by_lens,
        "stats_by_kind": _aggregate_by_kind(scored),
        "stats_by_branch_id": _aggregate_by_branch(scored),
        "summary": {
            "n_predictions": len(scored),
            "price_axis_HIT": price_hits,
            "price_axis_FAIL": price_fails,
            "price_axis_NEUTRAL_DRAW": price_neutral,
            "price_soft_hit_rate": round(price_soft, 4) if price_soft is not None else None,
        },
        "evolution_eligible": True,
        "risk_ack_ko": [
            "제안 JSON만 — go_no_go·실매매·Track A 자동 주입 금지",
            "human sign-off 없이 rules 파일 변경 없음",
        ],
    }


def _ko_direction(val: Any) -> str:
    raw = str(val or "—").strip().lower()
    table = {
        "up": "상승",
        "down": "하락",
        "bull": "상승",
        "bear": "하락",
        "neutral": "중립",
        "flat": "보합",
        "insufficient_data": "데이터 부족",
        "none": "—",
        "": "—",
    }
    return table.get(raw, str(val or "—"))


def _ko_lens(val: Any) -> str:
    raw = str(val or "").strip().lower()
    table = {
        "logos": "성경",
        "myeongni": "명리",
        "sasang": "사상",
        "price_btrack": "가격(B)",
        "market_myeongni": "시장명리",
    }
    return table.get(raw, str(val or "—"))


def _ko_dual_leg(val: Any) -> str:
    raw = str(val or "—").strip().lower()
    table = {
        "agree": "일치",
        "disagree": "불일치",
        "partial": "부분일치",
        "unknown": "미확인",
        "none": "—",
    }
    return table.get(raw, str(val or "—"))


def _fmt_soft_rate(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(v)


def build_evening_telegram(score: Dict[str, Any], *, evolution: Optional[Dict[str, Any]] = None) -> str:
    sm = score.get("summary") or {}
    ma = score.get("multi_asset") or {}
    ds = score.get("data_source") or {}
    bn = ds.get("binance_sidecar") if isinstance(ds.get("binance_sidecar"), dict) else {}
    lines = [
        f"🌙 MKM 저녁 채점 · {score.get('calendar_kst')}",
        "[가설] 연구 전용 · 실매매·압축A 자동 연동 없음",
        f"봉인 seal={score.get('seal_id')} · 예측 {sm.get('n_predictions')}건",
        f"코스피 {_ko_direction((ma.get('kospi') or {}).get('direction'))} "
        f"({(ma.get('kospi') or {}).get('return_pct')}%) · "
        f"비트코인 {_ko_direction((ma.get('btc') or {}).get('direction'))} "
        f"({(ma.get('btc') or {}).get('return_pct')}%)",
        f"가격축 적중={sm.get('price_axis_HIT')} 오적={sm.get('price_axis_FAIL')} "
        f"중립={sm.get('price_axis_NEUTRAL_DRAW')} 소프트={_fmt_soft_rate(sm.get('price_soft_hit_rate'))}",
    ]
    if bn.get("ok"):
        lines.append(
            f"바이낸스 섀도(관측) 일봉={_ko_direction((bn.get('latest_daily') or {}).get('direction'))} · "
            f"듀얼레그={_ko_dual_leg(bn.get('dual_leg_agreement'))}"
        )
    lines.extend(["", "▸ 렌즈별 소프트 적중"])
    for lens, st in sorted((score.get("stats_by_lens") or {}).items()):
        lines.append(
            f"  · {_ko_lens(lens)}: n={st.get('n')} 소프트={_fmt_soft_rate(st.get('soft_hit_rate'))}"
        )
    if evolution:
        props = evolution.get("proposals") or []
        if props:
            lines.extend(["", f"▸ 진화 제안(드라이런) {len(props)}건"])
            for p in props[:3]:
                if p.get("branch_id"):
                    lines.append(
                        f"  · 분기 {p.get('branch_id')}: {p.get('action')} "
                        f"소프트={_fmt_soft_rate(p.get('soft_rate'))}"
                    )
                else:
                    lines.append(
                        f"  · {_ko_lens(p.get('lens'))}/{p.get('kind')}: {p.get('action')} "
                        f"소프트={_fmt_soft_rate(p.get('soft_rate'))}"
                    )
    try:
        from scripts.a_code_evening_briefing_append_v1 import append_a_code_evening_lines  # noqa: WPS433

        append_a_code_evening_lines(lines, include_gate=True)
    except Exception:
        pass
    lines.extend(["", "[가설] 연구 전용 · 수동 승인 전 자동 승격 없음"])
    return "\n".join(lines)


def _refresh_market_csvs(workspace: Path = ROOT) -> Dict[str, Any]:
    import subprocess

    results: Dict[str, Any] = {}
    for name in ("fetch_kospi_yfinance_csv.py", "fetch_btc_yfinance_csv.py"):
        script = workspace / "scripts" / name
        if not script.is_file():
            results[name] = {"ok": False, "reason": "missing"}
            continue
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        results[name] = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-kst", default="", help="Seal date (default: today KST)")
    ap.add_argument("--seal-json", type=Path, default=None)
    ap.add_argument("--skip-market-fetch", action="store_true")
    ap.add_argument(
        "--include-binance-shadow",
        action="store_true",
        help="Fetch Binance public BTC shadow (non-SSOT dual-leg compare)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-telegram-json", action="store_true")
    args = ap.parse_args()

    if args.seal_json:
        seal_path = args.seal_json
    else:
        cal = args.date_kst or datetime.now(KST).strftime("%Y-%m-%d")
        seal_path = resolve_research_seal(cal)

    if not seal_path.is_file():
        raise SystemExit(f"missing research seal: {seal_path}")

    if not args.skip_market_fetch:
        fetches = _refresh_market_csvs()
        for name, st in fetches.items():
            if not st.get("ok"):
                print(f"WARN: {name} exit={st.get('exit_code')}", file=sys.stderr)

    doc = score_research_evening(seal_path, include_binance_shadow=args.include_binance_shadow)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cal = doc.get("calendar_kst")
    if cal:
        archive = BRIEFING_LOG / f"{cal}_evening_multi_lens_score_v1.json"
        archive.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_telegram_json:
        tg = ROOT / "reports" / "commander_evening_telegram_preview_latest.json"
        tg.write_text(
            json.dumps({"text": build_evening_telegram(doc)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    sm = doc.get("summary") or {}
    print(
        f"WROTE: {args.out_json} seal={doc.get('seal_id')} "
        f"price_soft={sm.get('price_soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
