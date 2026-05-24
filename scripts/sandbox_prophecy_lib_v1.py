"""Shared helpers for Prophecy Sandbox (research_only, isolated from prod score)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SANDBOX_TIER = "SANDBOX"
SANDBOX_LABEL = "[SANDBOX][HYPO]"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot_calendar_date_utc(generated_at_utc: str | None = None) -> str:
    """UTC calendar day for rollup/holdout dedupe (YYYY-MM-DD)."""
    ts = str(generated_at_utc or utc_now())
    return ts[:10] if len(ts) >= 10 else ts


def finalize_stream_row(row: dict[str, Any]) -> dict[str, Any]:
    """Attach explicit calendar key so multiple same-day runs dedupe correctly."""
    row.setdefault(
        "snapshot_calendar_date_utc",
        snapshot_calendar_date_utc(str(row.get("generated_at_utc") or "")),
    )
    return row


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)


def tag_hypothesis_sandbox(doc: dict[str, Any], *, target_id: str, lens_profile: str) -> dict[str, Any]:
    out = json.loads(json.dumps(doc, ensure_ascii=False))
    out["hypothesis_tier"] = SANDBOX_TIER
    lab = str(out.get("label") or "")
    if SANDBOX_LABEL not in lab:
        out["label"] = f"{SANDBOX_LABEL} {lab}".strip()
    out["sandbox_meta"] = {
        "target_id": target_id,
        "lens_profile": lens_profile,
        "track_wall": {
            "prod_score_mutation": False,
            "track_a_auto_bridge": False,
            "live_trading": False,
        },
    }
    return out


def profile_cfg(base: dict[str, Any], profile: str) -> dict[str, Any]:
    cfg = json.loads(json.dumps(base, ensure_ascii=False))
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    rules["price_instrument"] = "btc"
    rules["enforce_btc_only_guard"] = False
    if profile == "v1_price_only":
        rules["ensemble_mode"] = "v1"
        cfg["weights"] = {"price": 1.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 0.0}
    elif profile == "v2_confidence_fusion":
        rules["ensemble_mode"] = "v2_confidence_fusion"
    elif profile == "v1_myeongni_sasang":
        rules["ensemble_mode"] = "v1"
        cfg["weights"] = {"price": 0.0, "macro": 0.0, "news": 0.0, "myeongni_sasang": 1.0}
    elif profile == "v2_price_macro_news":
        rules["ensemble_mode"] = "v2_confidence_fusion"
        cfg["weights_v2"] = {
            "price": 0.7,
            "macro": 0.18,
            "news": 0.12,
            "myeongni": 0.0,
            "sasang": 0.0,
            "logos": 0.0,
        }
    elif profile == "v2_sasang_price":
        rules["ensemble_mode"] = "v2_confidence_fusion"
        cfg["weights_v2"] = {
            "price": 0.4,
            "sasang": 0.45,
            "macro": 0.08,
            "news": 0.07,
            "myeongni": 0.0,
            "logos": 0.0,
        }
    else:
        raise ValueError(f"unknown sandbox profile: {profile}")
    cfg["rules"] = rules
    return cfg


def default_targets() -> list[dict[str, Any]]:
    return [
        {
            "target_id": "btc_v1_price_only",
            "asset": "btc",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "kospi_csv": None,
        },
        {
            "target_id": "btc_v2_confidence_fusion",
            "asset": "btc",
            "instrument": "btc",
            "lens_profile": "v2_confidence_fusion",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "kospi_csv": None,
        },
        {
            "target_id": "kospi_v1_myeongni_sasang",
            "asset": "kospi",
            "instrument": "kospi",
            "lens_profile": "v1_myeongni_sasang",
            "btc_csv": None,
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
        {
            "target_id": "eth_v1_price_only",
            "asset": "eth",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/eth_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
            "note": "ETH leg via btc-csv loader shape; kospi csv used only for calendar intersection when dual",
        },
        {
            "target_id": "eth_v1_myeongni_sasang",
            "asset": "eth",
            "instrument": "btc",
            "lens_profile": "v1_myeongni_sasang",
            "btc_csv": "research/market_data/eth_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
            "note": "ETH + 명리·사상 융합(SANDBOX); research_only.",
        },
        {
            "target_id": "sol_v1_price_only",
            "asset": "sol",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/sol_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
        {
            "target_id": "gld_v1_price_only",
            "asset": "gold",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/gld_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
            "note": "Gold proxy via GLD ETF OHLCV (research_only).",
        },
        {
            "target_id": "btc_v2_price_macro_news",
            "asset": "btc",
            "instrument": "btc",
            "lens_profile": "v2_price_macro_news",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "kospi_csv": None,
        },
        {
            "target_id": "kospi_v1_price_only",
            "asset": "kospi",
            "instrument": "kospi",
            "lens_profile": "v1_price_only",
            "btc_csv": None,
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
        {
            "target_id": "ndx_v1_price_only",
            "asset": "ndx",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/ndx_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
        {
            "target_id": "btc_v2_sasang_price",
            "asset": "btc",
            "instrument": "btc",
            "lens_profile": "v2_sasang_price",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "kospi_csv": None,
        },
        {
            "target_id": "btc_v1_myeongni_sasang",
            "asset": "btc",
            "instrument": "btc",
            "lens_profile": "v1_myeongni_sasang",
            "btc_csv": "research/market_data/btc_daily_external_yf.csv",
            "kospi_csv": None,
        },
        {
            "target_id": "qqq_v1_price_only",
            "asset": "qqq",
            "instrument": "btc",
            "lens_profile": "v1_price_only",
            "btc_csv": "research/market_data/qqq_daily_external_yf.csv",
            "kospi_csv": "research/market_data/kospi_daily_external_yf.csv",
        },
    ]


def phase3_sensor_targets() -> list[dict[str, Any]]:
    """Sensor-only sandbox legs (no prod score mutation)."""
    base = [
        {
            "target_id": "btc_phase3_funding_skew",
            "mode": "phase3_sensor",
            "asset": "btc",
            "lens_profile": "phase3_perp_funding_skew",
            "sensor_z_key": "perp_funding_skew_signed_flow_z",
        },
        {
            "target_id": "btc_phase3_onchain_netflow",
            "mode": "phase3_sensor",
            "asset": "btc",
            "lens_profile": "phase3_onchain_netflow",
            "sensor_z_key": "onchain_exchange_netflow_signed_flow_z",
        },
        {
            "target_id": "btc_phase3_composite_flow",
            "mode": "phase3_sensor",
            "asset": "btc",
            "lens_profile": "phase3_composite_flow",
            "sensor_z_key": "leading_composite_signed_flow_z",
        },
    ]
    inverted: list[dict[str, Any]] = []
    deadbanded: list[dict[str, Any]] = []
    for t in base:
        inv = dict(t)
        inv["target_id"] = f"{t['target_id']}_invert"
        inv["lens_profile"] = f"{t['lens_profile']}_invert"
        inv["invert"] = True
        inverted.append(inv)
        for db in (0.1, 0.2):
            dbt = dict(t)
            suffix = f"db{int(round(db * 10)):02d}"
            dbt["target_id"] = f"{t['target_id']}_{suffix}"
            dbt["lens_profile"] = f"{t['lens_profile']}_{suffix}"
            dbt["deadband"] = db
            deadbanded.append(dbt)
    return base + inverted + deadbanded


def sasang_dynamics_targets() -> list[dict[str, Any]]:
    root = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
    sasang_path = str(root.relative_to(ROOT)).replace("\\", "/")
    return [
        {
            "target_id": "btc_sasang_mapping_target",
            "mode": "sasang_dynamics",
            "asset": "btc",
            "lens_profile": "sasang_mapping_target",
            "strategy": "mapping_target",
            "sasang_jsonl": sasang_path,
        },
        {
            "target_id": "btc_sasang_heat_cold_sign",
            "mode": "sasang_dynamics",
            "asset": "btc",
            "lens_profile": "sasang_heat_cold_sign",
            "strategy": "heat_cold_sign",
            "sasang_jsonl": sasang_path,
        },
    ]


def all_targets() -> list[dict[str, Any]]:
    return default_targets() + phase3_sensor_targets() + sasang_dynamics_targets()
