#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PGAE Evolution Loop (Phase 3)

목적: 예언 vs 실제 수익률 일일 복기 → 14B 분석 → 가중치 갱신 제안
- 일일 복기: 예언 방향 vs 실제 PnL 비교
- 14B 분석: "왜 달랐는가?" 한 문장 제언
- 가중치 갱신: strategy_params.json 또는 evolution_log에 제안 저장

작성일: 2026-03-02
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent.parent


def _load_prophecy_context() -> Dict[str, Any]:
    """예언 컨텍스트 로드 (prophecy_sync 의존)"""
    try:
        from src.integration.prophecy_sync import load_prophecy_context
        return load_prophecy_context()
    except ImportError:
        # 상대 경로 fallback
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.integration.prophecy_sync import load_prophecy_context
        return load_prophecy_context()


def _load_daily_metrics(target_date: Optional[str] = None) -> Dict[str, Any]:
    """일일 수익 메트릭 로드 (DailyRevenueTracker 또는 파일)"""
    data_dir = PROJECT_ROOT / "data" / "revenue_tracking"
    metrics_file = data_dir / "daily_metrics.json"
    history_file = data_dir / "revenue_history.json"
    date_str = target_date or datetime.now().strftime("%Y-%m-%d")

    # 오늘 메트릭
    if metrics_file.exists():
        try:
            metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            if metrics.get("current_date") == date_str:
                return metrics
        except Exception:
            pass

    # 과거 날짜: revenue_history에서 검색
    if history_file.exists() and date_str != datetime.now().strftime("%Y-%m-%d"):
        try:
            history = json.loads(history_file.read_text(encoding="utf-8"))
            for m in (history or []):
                if m.get("current_date") == date_str:
                    return m
        except Exception:
            pass

    return {
        "current_date": date_str,
        "daily_pnl": 0.0,
        "daily_return": 0.0,
        "total_trades": 0,
        "win_rate": 0.0,
    }


def _load_trades_for_date(target_date: str) -> List[Dict[str, Any]]:
    """특정 날짜의 거래 내역 로드"""
    log_dir = PROJECT_ROOT / "logs"
    trades_file = log_dir / "live_trades_history.json"
    if not trades_file.exists():
        return []

    try:
        trades = json.loads(trades_file.read_text(encoding="utf-8"))
        if not isinstance(trades, list):
            return []

        # target_date (YYYY-MM-DD)에 해당하는 거래만 필터
        filtered = []
        for t in trades:
            ts = t.get("timestamp") or t.get("close_time") or t.get("time")
            if ts is None:
                continue
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
            else:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.strftime("%Y-%m-%d") == target_date:
                filtered.append(t)
        return filtered
    except Exception as e:
        logger.warning("거래 내역 로드 실패: %s", e)
        return []


def _get_14b_analysis(prompt: str) -> Optional[str]:
    """14B 한 문장 제언 (선택적, 실패 시 None)"""
    try:
        from src.config.config_loader import ConfigLoader
        from src.llm.llm_14b_advisory import get_14b_advisory

        loader = ConfigLoader()
        loader.load()
        call_path = loader.get_14b_4d_native_call_path()
        if not call_path:
            logger.debug("14B call_path 없음(설정 비활성화) → 스킵")
            return None
        return get_14b_advisory(prompt, call_path, timeout_sec=180, workspace_root=WORKSPACE_ROOT)
    except Exception as e:
        logger.warning("14B 분석 스킵: %s", e)
        return None


def run_daily_review(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    PGAE 일일 복기 실행.

    Args:
        target_date: 복기 대상 날짜 (YYYY-MM-DD). None이면 오늘.

    Returns:
        복기 결과 (prophecy, actual, comparison, 14b_advisory, suggested_adjustments)
    """
    date_str = target_date or datetime.now().strftime("%Y-%m-%d")

    # 0. 14B 서버 워밍업 (Option B: server_url 설정 시 cold start 완화)
    try:
        from src.llm.llm_14b_advisory import warmup_14b_server_if_configured
        warmup_14b_server_if_configured()
    except Exception as e:
        logger.debug("14B 워밍업 스킵: %s", e)

    # 1. 예언 컨텍스트
    prophecy = _load_prophecy_context()
    prophecy_direction = prophecy.get("prophecy_direction", "NEUTRAL")
    crisis_level = prophecy.get("crisis_level", "UNKNOWN")
    today_summary = prophecy.get("today_summary", "")

    # 2. 실제 메트릭
    metrics = _load_daily_metrics(date_str)
    daily_pnl = metrics.get("daily_pnl", 0.0)
    daily_return = metrics.get("daily_return", 0.0)
    win_rate = metrics.get("win_rate", 0.0)
    total_trades = metrics.get("total_trades", 0)

    # 3. 해당 날짜 거래 (메트릭이 오늘 기준이면 trades는 별도)
    trades = _load_trades_for_date(date_str)
    if trades:
        winning = sum(1 for t in trades if t.get("net_pnl", 0) > 0)
        actual_win_rate = (winning / len(trades) * 100) if trades else 0.0
        actual_pnl = sum(t.get("net_pnl", 0) for t in trades)
    else:
        actual_win_rate = win_rate
        actual_pnl = daily_pnl

    # 4. 예언 vs 실제 비교
    # CAUTION_DOWN: 예언이 하락 경고 → 실제가 양수면 "예언과 상반"
    # NEUTRAL: 예언이 중립 → 큰 손실이면 "예언 미반영"
    comparison = {
        "prophecy_direction": prophecy_direction,
        "actual_pnl": actual_pnl,
        "actual_return_pct": daily_return,
        "actual_win_rate": actual_win_rate,
        "total_trades": total_trades or len(trades),
        "alignment": "UNKNOWN",
        "note": "",
    }

    if prophecy_direction == "CAUTION_DOWN" and actual_pnl > 0:
        comparison["alignment"] = "OPPOSITE"
        comparison["note"] = "예언은 하락 경고였으나 실제 수익 발생"
    elif prophecy_direction == "CAUTION_DOWN" and actual_pnl < 0:
        comparison["alignment"] = "ALIGNED"
        comparison["note"] = "예언 하락 경고와 실제 손실 일치"
    elif prophecy_direction == "NEUTRAL":
        if actual_pnl < -50:  # 큰 손실
            comparison["alignment"] = "UNEXPECTED_LOSS"
            comparison["note"] = "예언 중립이나 실제 손실 발생"
        else:
            comparison["alignment"] = "NEUTRAL"
            comparison["note"] = "예언 중립, 실제도 중립 수준"
    else:
        comparison["alignment"] = "NEUTRAL"
        comparison["note"] = "예언/실제 비교 불명확"

    # 5. 14B 분석 ("왜 달랐는가?")
    prompt = (
        f"오늘({date_str}) 예언: {crisis_level}, 방향={prophecy_direction}. "
        f"실제: PnL={actual_pnl:.2f} USDT, 수익률={daily_return:.2f}%, 승률={actual_win_rate:.1f}%. "
        f"비교: {comparison['alignment']} - {comparison['note']}. "
        "예언과 실제가 다른 이유를 한 문장으로 제언해줘."
    )
    advisory = _get_14b_analysis(prompt)

    # 6. 가중치 갱신 제안 (보수적: 로그만, 자동 적용 안 함)
    suggested_adjustments: Dict[str, Any] = {}
    if comparison["alignment"] == "OPPOSITE":
        suggested_adjustments["note"] = "예언 하락 시 공격적 매수 신호 완화 검토"
    elif comparison["alignment"] == "UNEXPECTED_LOSS":
        suggested_adjustments["note"] = "중립 예언일 때 손절 강화 검토"

    result = {
        "date": date_str,
        "timestamp": datetime.now().isoformat(),
        "prophecy": {
            "direction": prophecy_direction,
            "crisis_level": crisis_level,
            "today_summary": today_summary[:200],
        },
        "actual": {
            "daily_pnl": daily_pnl,
            "daily_return": daily_return,
            "win_rate": win_rate,
            "total_trades": total_trades or len(trades),
        },
        "comparison": comparison,
        "14b_advisory": advisory,
        "suggested_adjustments": suggested_adjustments,
    }

    # 7. evolution_log 저장
    _save_evolution_log(result)

    logger.info(
        "PGAE 일일 복기 완료: %s | 예언=%s vs 실제 PnL=%.2f | 정렬=%s",
        date_str, prophecy_direction, actual_pnl, comparison["alignment"]
    )
    return result


def _save_evolution_log(result: Dict[str, Any]) -> None:
    """evolution_log에 복기 결과 추가"""
    data_dir = PROJECT_ROOT / "data" / "evolution"
    data_dir.mkdir(parents=True, exist_ok=True)
    log_file = data_dir / "pgae_evolution_log.json"

    history: List[Dict[str, Any]] = []
    if log_file.exists():
        try:
            history = json.loads(log_file.read_text(encoding="utf-8"))
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []

    history.append(result)
    # 최근 90일만 유지
    if len(history) > 90:
        history = history[-90:]

    log_file.write_text(
        json.dumps(history, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def run_weight_update_suggestion(
    evolution_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    최근 evolution_log를 기반으로 strategy_params 갱신 제안 생성.
    자동 적용하지 않고, 제안만 반환.
    """
    log_path = evolution_log_path or (PROJECT_ROOT / "data" / "evolution" / "pgae_evolution_log.json")
    if not log_path.exists():
        return {"status": "no_log", "message": "evolution_log 없음"}

    try:
        history = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(history, list) or len(history) < 3:
            return {"status": "insufficient_data", "message": "최소 3일치 데이터 필요"}

        # 최근 7일 분석
        recent = history[-7:]
        opposite_count = sum(1 for r in recent if r.get("comparison", {}).get("alignment") == "OPPOSITE")
        unexpected_loss = sum(1 for r in recent if r.get("comparison", {}).get("alignment") == "UNEXPECTED_LOSS")

        suggestions = []
        if opposite_count >= 3:
            suggestions.append({
                "target": "signal_generation.min_confidence",
                "action": "increase",
                "reason": "예언 하락 시 수익 발생 빈도 높음 → 신호 필터 강화",
            })
        if unexpected_loss >= 2:
            suggestions.append({
                "target": "risk_management.stop_loss_ratio",
                "action": "decrease",
                "reason": "중립 예언일 때 손실 빈도 → 손절 강화",
            })

        return {
            "status": "ok",
            "period": "7d",
            "suggestions": suggestions,
            "summary": f"OPPOSITE={opposite_count}, UNEXPECTED_LOSS={unexpected_loss}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="PGAE 일일 복기 (Evolution Loop)")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="복기 대상 날짜 (YYYY-MM-DD). 미지정 시 어제.",
    )
    args = parser.parse_args()

    target = args.date
    if not target:
        target = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    result = run_daily_review(target_date=target)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
