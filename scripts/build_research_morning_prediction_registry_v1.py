#!/usr/bin/env python3
"""R-IBL morning prediction registry — seal multi-lens B-track claims for evening scoring [HYPO]."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"
DEFAULT_LATEST = REPORTS / "research_morning_prediction_registry_latest.json"
SEAL_DIR = REPORTS / "briefing_log"
SCHEMA = "research_morning_prediction_registry_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _direction_from_score(score: Any) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "watch"
    if s > 0.08:
        return "bull"
    if s < -0.08:
        return "bear"
    return "neutral"


def _pred(
    *,
    prediction_id: str,
    lens: str,
    kind: str,
    claim_ko: str,
    score_against: str,
    evidence_path: str = "",
    direction_proxy: Optional[str] = None,
    confidence: Any = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "prediction_id": prediction_id,
        "lens": lens,
        "kind": kind,
        "claim_ko": claim_ko,
        "score_against": score_against,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
    }
    if evidence_path:
        row["evidence_path"] = evidence_path
    if direction_proxy is not None:
        row["direction_proxy"] = direction_proxy
    if confidence is not None:
        row["confidence"] = confidence
    return row


def _collect_logos(workspace: Path, cal: str, out: List[Dict[str, Any]]) -> None:
    logos = _read_json(ART / "logos_independent_lens_latest.json")
    if logos:
        scores = logos.get("scores") or {}
        ds = scores.get("direction_score")
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_logos_lens_direction",
                lens="logos",
                kind="lens_direction_score",
                claim_ko=(
                    f"성경(Logos) 독립 렌즈 방향 { _direction_from_score(ds) } "
                    f"(score={ds}, conf={scores.get('confidence')}) [NON_GATING]"
                ),
                score_against=_rel(workspace / "research" / "market_data" / "kospi_daily_external_yf.csv"),
                evidence_path=_rel(ART / "logos_independent_lens_latest.json"),
                direction_proxy=_direction_from_score(ds),
                confidence=scores.get("confidence"),
            )
        )

    replay = _read_json(REPORTS / "subgraph_router_replay_summary_latest.json")
    for row in replay.get("rows") or []:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("query_id") or "qx")
        if not row.get("pass"):
            continue
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_logos_graphrag_{qid}",
                lens="logos",
                kind="graphrag_path_hit",
                claim_ko=(
                    f"Logos GraphRAG {qid}: bridge {row.get('bridges_matched')} · "
                    f"path {row.get('paths_count')} [가설·해설]"
                ),
                score_against=_rel(workspace / "docs" / "final" / "fixtures" / "logos_gold_query_eval_v1.json"),
                evidence_path=str(row.get("out_json") or "").replace("\\", "/"),
                confidence="mid" if row.get("paths_count", 0) >= 1 else "low",
            )
        )

    gold = _read_json(REPORTS / "logos_gold_query_eval_v1_latest.json")
    if gold.get("summary", {}).get("gold_required_all_pass"):
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_logos_gold_cpu_eval",
                lens="logos",
                kind="graphrag_gold_eval",
                claim_ko="Logos CPU gold eval: gold_required 전항 pass [NON_GATING]",
                score_against=_rel(REPORTS / "logos_gold_query_eval_v1_latest.json"),
                evidence_path=_rel(REPORTS / "logos_gold_query_eval_v1_latest.json"),
                confidence="high",
            )
        )


def _collect_myeongni(workspace: Path, cal: str, out: List[Dict[str, Any]]) -> None:
    myeongni = _read_json(ART / "myeongni_independent_lens_latest.json")
    if myeongni:
        scores = myeongni.get("scores") or {}
        ds = scores.get("direction_score")
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_myeongni_lens_direction",
                lens="myeongni",
                kind="direction_mdd",
                claim_ko=(
                    f"명리 독립 렌즈 중기 방향 {_direction_from_score(ds)} "
                    f"(score={ds}, conf={scores.get('confidence')})"
                ),
                score_against=_rel(workspace / "research" / "market_data" / "kospi_daily_external_yf.csv"),
                evidence_path=_rel(ART / "myeongni_independent_lens_latest.json"),
                direction_proxy=_direction_from_score(ds),
                confidence=scores.get("confidence"),
            )
        )

    stream = _read_json(REPORTS / "commander_hypothesis_stream_latest.json")
    for br in stream.get("branches") or []:
        if not isinstance(br, dict):
            continue
        bid = str(br.get("branch_id") or "branch")
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_myeongni_branch_{bid}",
                lens="myeongni",
                kind="hypothesis_stream_branch",
                claim_ko=f"{br.get('trigger_ko', '')} → {br.get('predicted_bias_ko', '')}",
                score_against="behavioral_proxy:kospi_direction",
                evidence_path=_rel(REPORTS / "commander_hypothesis_stream_latest.json"),
                confidence=br.get("confidence"),
            )
        )
    syn = stream.get("synthesis_ko")
    if syn:
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_myeongni_synthesis",
                lens="myeongni",
                kind="narrative_hypothesis",
                claim_ko=str(syn)[:280],
                score_against="behavioral_proxy:kospi_direction",
                evidence_path=_rel(REPORTS / "commander_hypothesis_stream_latest.json"),
                confidence="mid",
            )
        )


def _collect_sasang(workspace: Path, cal: str, out: List[Dict[str, Any]]) -> None:
    sasang = _read_json(ART / "sasang_independent_lens_latest.json")
    if not sasang:
        return
    scores = sasang.get("scores") or {}
    ds = scores.get("direction_score")
    stream = sasang.get("sasang_stream_outputs") or {}
    regime = stream.get("regime_hypothesis") or "—"
    out.append(
        _pred(
            prediction_id=f"pred_{cal}_sasang_lens_bundle",
            lens="sasang",
            kind="regime_intensity",
            claim_ko=(
                f"사상 렌즈 regime={regime} · mapping={stream.get('mapping_target')} "
                f"· 방향프록시 {_direction_from_score(ds)}"
            ),
            score_against=_rel(workspace / "research" / "market_data" / "kospi_daily_external_yf.csv"),
            evidence_path=_rel(ART / "sasang_independent_lens_latest.json"),
            direction_proxy=_direction_from_score(ds),
            confidence=scores.get("confidence"),
        )
    )


def _collect_price_btrack(workspace: Path, cal: str, out: List[Dict[str, Any]]) -> None:
    hypo = _read_json(ART / "btrack_hypothesis_prophecy_latest.json")
    pred = hypo.get("prediction") or {}
    if pred.get("direction"):
        inst = str(pred.get("instrument") or "multi").lower()
        against = _rel(workspace / "research" / "market_data" / "kospi_daily_external_yf.csv")
        if "btc" in inst or inst == "multi":
            against += "," + _rel(workspace / "research" / "market_data" / "btc_daily_external_yf.csv")
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_price_btrack_hypothesis",
                lens="price_btrack",
                kind="kospi_directional" if inst == "kospi" else "multi_asset_directional",
                claim_ko=f"B-track 앙상블 가설 {inst} · {pred.get('direction')} (conf={pred.get('confidence')})",
                score_against=against,
                evidence_path=_rel(ART / "btrack_hypothesis_prophecy_latest.json"),
                direction_proxy=str(pred.get("direction")),
                confidence=pred.get("confidence"),
            )
        )

    brief = _read_json(ART / "internal_kospi_morning_brief_onepager_latest.json")
    if brief.get("today_action"):
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_price_kospi_morning_action",
                lens="price_btrack",
                kind="kospi_morning_action",
                claim_ko=f"장전 코스피 관측 액션 {brief.get('today_action')} (확신 {brief.get('confidence_0_100')}/100)",
                score_against=_rel(workspace / "research" / "market_data" / "kospi_daily_external_yf.csv"),
                evidence_path=_rel(ART / "internal_kospi_morning_brief_onepager_latest.json"),
                direction_proxy=str(brief.get("today_action")),
                confidence=brief.get("confidence_0_100"),
            )
        )

    shadow = _read_json(ART / "prophecy_shadow_panel_eval_v1_latest.json")
    baseline = (shadow.get("baseline") or {}).get("metrics") or {}
    if baseline.get("n_evaluated"):
        hr = baseline.get("price_directional_hit_rate")
        out.append(
            _pred(
                prediction_id=f"pred_{cal}_price_shadow_panel_baseline",
                lens="price_btrack",
                kind="shadow_panel_baseline",
                claim_ko=f"Shadow panel baseline 적중 {float(hr)*100:.1f}% (n={baseline.get('n_evaluated')})",
                score_against=_rel(ART / "prophecy_shadow_panel_eval_v1_latest.json"),
                evidence_path=_rel(ART / "prophecy_shadow_panel_eval_v1_latest.json"),
                confidence=hr,
            )
        )


def build_registry(workspace: Path = ROOT, *, calendar_kst: Optional[str] = None) -> Dict[str, Any]:
    cal = calendar_kst or datetime.now(KST).strftime("%Y-%m-%d")
    predictions: List[Dict[str, Any]] = []
    _collect_logos(workspace, cal, predictions)
    _collect_myeongni(workspace, cal, predictions)
    _collect_sasang(workspace, cal, predictions)
    _collect_price_btrack(workspace, cal, predictions)

    payload = json.dumps({"d": cal, "p": predictions}, ensure_ascii=False, sort_keys=True)
    seal_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    by_lens: Dict[str, int] = {}
    for p in predictions:
        lens = str(p.get("lens") or "unknown")
        by_lens[lens] = by_lens.get(lens, 0) + 1

    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "track_a_auto_merge_forbidden": True,
        "live_trading_trigger_forbidden": True,
        "calendar_kst": cal,
        "seal_id": seal_id,
        "generated_at_utc": _utc_now(),
        "n_predictions": len(predictions),
        "predictions_by_lens": by_lens,
        "predictions": predictions,
        "evening_score_note_ko": f"저녁 채점 대상 seal_id={seal_id} · R-IBL research_only",
        "sources_scanned": [
            "docs/final/artifacts/logos_independent_lens_latest.json",
            "reports/subgraph_router_replay_summary_latest.json",
            "docs/final/artifacts/myeongni_independent_lens_latest.json",
            "reports/commander_hypothesis_stream_latest.json",
            "docs/final/artifacts/sasang_independent_lens_latest.json",
            "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
            "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json",
            "docs/final/artifacts/prophecy_shadow_panel_eval_v1_latest.json",
        ],
    }


def _snapshot_market_seal(workspace: Path, calendar_kst: str) -> Optional[Dict[str, Any]]:
    """Embed morning BTC/KOSPI anchor for evening R-IBL score (best-effort)."""
    arch = workspace / "reports" / "briefing_log" / f"{calendar_kst}_morning_briefing_v1.json"
    if arch.is_file():
        env = _read_json(arch)
        briefing = env.get("briefing") or env
        ms = briefing.get("market_seal")
        if isinstance(ms, dict):
            return ms
    latest = workspace / "reports" / "commander_morning_briefing_latest.json"
    if latest.is_file():
        env = _read_json(latest)
        if str(env.get("calendar_kst") or (env.get("briefing") or {}).get("calendar_kst")) == calendar_kst:
            briefing = env.get("briefing") or env
            ms = briefing.get("market_seal")
            if isinstance(ms, dict):
                return ms
    try:
        from scripts.multi_asset_market_adapter_v1 import fetch_market_seal  # noqa: WPS433

        return fetch_market_seal()
    except Exception:
        return None


def write_registry(doc: Dict[str, Any], workspace: Path = ROOT) -> tuple[Path, Path]:
    latest = workspace / "reports" / "research_morning_prediction_registry_latest.json"
    seal_dir = workspace / "reports" / "briefing_log"
    seal_dir.mkdir(parents=True, exist_ok=True)
    cal = str(doc.get("calendar_kst") or datetime.now(KST).strftime("%Y-%m-%d"))
    seal = seal_dir / f"{cal}_research_seal_v1.json"
    market_seal = _snapshot_market_seal(workspace, cal)
    envelope: Dict[str, Any] = {
        "schema": "research_morning_seal_archive_v1",
        "calendar_kst": cal,
        "archived_at_utc": _utc_now(),
        "registry": doc,
    }
    if market_seal:
        envelope["market_seal"] = market_seal
        doc["market_seal_source"] = "embedded_at_seal_archive"
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(text, encoding="utf-8")
    seal.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return latest, seal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--calendar-kst", default=None)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()
    ws = args.workspace_root.resolve()
    doc = build_registry(ws, calendar_kst=args.calendar_kst)
    if args.stdout_only:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    latest, seal = write_registry(doc, ws)
    print(f"WROTE: {latest} n_predictions={doc.get('n_predictions')} seal_id={doc.get('seal_id')}")
    print(f"WROTE: {seal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
