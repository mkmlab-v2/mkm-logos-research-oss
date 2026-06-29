#!/usr/bin/env python3
"""Assemble Lens Sovereignty supplementary rails v1.2 [HYPO][research_only].

SSOT-first (no daily re-fetch): reads accumulated training/eval artifacts on disk.
Sasang: emotion_weight_memory weekly + multisource sentiment JSONL.
Myeongni: weather fusion profile + general_prophecy Brier + session/weather join meta.
Logos: chronology era blind eval + historical holdout Brier dual report.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_sovereignty_supplementary_rails_v1_2_latest.json"

EMOTION_WEEKLY = ROOT / "docs/final/artifacts/emotion_weight_memory_weekly_report_latest.json"
MULTISOURCE_SENTIMENT = (
    ROOT / "projects/bitcoin-trading/memory/v2/emotion/operational_multisource_sentiment_daily_latest.jsonl"
)
ATPROTO_DIR = ROOT / "projects/bitcoin-trading/memory/v2/btrack/raw_feeds/atproto"

WEATHER_FUSION = ROOT / "docs/final/artifacts/myeongni_weather_fusion_profile_latest.json"
PROMOTION_GATE = ROOT / "docs/final/artifacts/myeongni_promotion_gate_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
BRIER_EVAL = ROOT / "docs/final/artifacts/general_prophecy_brier_eval_latest.json"
HOLDOUT_REPORT = ROOT / "docs/final/artifacts/general_prophecy_explainability_holdout_report_v1_latest.json"
WEATHER_CORR_JSON = ROOT / "reports/btrack_joined_wide_correlation_latest.json"
FULL_WINDOW_FUSION = ROOT / "reports/myeongni_full_window_disaster_risk_fusion_v1_latest.json"
PACK0B_SMOKE_EVAL = ROOT / "reports/myeongri_deterministic_lora_locked_eval_inference_eval_smoke100_latest.json"
PACK0B_FINAL_EVAL = ROOT / "reports/myeongri_deterministic_lora_locked_eval_inference_eval_latest.json"
PACK0B_WATCH = ROOT / "reports/pack0b_full500_ordered_watch_latest.json"
SASANG_HOLDOUT_AUDIT = ROOT / "reports/sasang_intensity_proxy_holdout_audit_v1_latest.json"
HORIZON_EVAL_V2 = ROOT / "docs/final/artifacts/three_lens_horizon_empirical_eval_v2_latest.json"

CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_era_blind_eval_text_blind_v1_latest.json"
HIST_BRIER = ROOT / "reports/biblical_history_holdout_brier_dual_report_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _latest_glob(pattern: str) -> Path | None:
    hits = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return hits[0] if hits else None


def _build_sasang_sentiment_rail() -> dict[str, Any]:
    out: dict[str, Any] = {
        "rail_id": "sasang_sentiment_external_v1_2",
        "eval_task": "multisource emotion/sentiment vs forward PnL proxy (weekly SSOT)",
        "ssot_primary": str(EMOTION_WEEKLY),
    }

    if EMOTION_WEEKLY.is_file():
        rep = _load_json(EMOTION_WEEKLY)
        gate = rep.get("gate_hint") if isinstance(rep.get("gate_hint"), dict) else {}
        metrics = rep.get("metrics") if isinstance(rep.get("metrics"), dict) else {}
        kpi = (rep.get("metrics_by_source") or {}).get("kpi_derived_sentiment_proxy_v1") or {}
        kpi_m = kpi.get("metrics") if isinstance(kpi.get("metrics"), dict) else {}
        out["emotion_weekly_ssot"] = {
            "path": str(EMOTION_WEEKLY),
            "n_total": rep.get("n_total"),
            "n_usable": rep.get("n_usable"),
            "coverage_ratio": rep.get("coverage_ratio"),
            "corr_valence_vs_forward_pnl_1d": metrics.get("corr_valence_vs_forward_pnl_1d"),
            "gate_recommended": gate.get("recommended"),
            "kpi_derived_n_usable": kpi.get("n_usable"),
            "kpi_corr_valence_vs_forward_pnl_1d": kpi_m.get("corr_valence_vs_forward_pnl_1d"),
        }
        thresholds = gate.get("thresholds") if isinstance(gate.get("thresholds"), dict) else {}
        min_n = int(thresholds.get("min_samples") or 30)
        min_cov = float(thresholds.get("min_coverage_ratio") or 0.8)
        min_corr = float(thresholds.get("min_corr_valence_vs_forward_pnl_1d") or 0.05)
        n_usable = int(rep.get("n_usable") or 0)
        cov = float(rep.get("coverage_ratio") or 0.0)
        corr = float(metrics.get("corr_valence_vs_forward_pnl_1d") or 0.0)
        pass_gate = n_usable >= min_n and cov >= min_cov and corr >= min_corr
        out["contract_pass"] = pass_gate
        out["status"] = "ok"
        out["pass_gate"] = {
            "min_samples": min_n,
            "min_coverage_ratio": min_cov,
            "min_corr_valence_vs_forward_pnl_1d": min_corr,
        }
    else:
        out["emotion_weekly_ssot"] = {"path": str(EMOTION_WEEKLY), "present": False}
        out["contract_pass"] = None
        out["status"] = "missing_ssot"

    if MULTISOURCE_SENTIMENT.is_file():
        lines = [ln for ln in MULTISOURCE_SENTIMENT.read_text(encoding="utf-8").splitlines() if ln.strip()]
        out["multisource_sentiment_jsonl"] = {
            "path": str(MULTISOURCE_SENTIMENT),
            "rows": len(lines),
        }
    atproto_files = list(ATPROTO_DIR.glob("*_atproto_sentiment_raw.jsonl"))
    out["atproto_raw_feed"] = {
        "path": str(ATPROTO_DIR),
        "n_daily_files": len(atproto_files),
        "note": "raw probe only — not primary SSOT for sovereignty rail",
    }
    out["note"] = (
        "Primary = emotion_weight_memory_weekly_report (701-row multisource pipeline). "
        "Do not re-count 3 atproto raw files as full sentiment history."
    )
    if SASANG_HOLDOUT_AUDIT.is_file():
        ha = _load_json(SASANG_HOLDOUT_AUDIT)
        out["intensity_holdout_audit"] = {
            "path": str(SASANG_HOLDOUT_AUDIT),
            "verdict": ha.get("verdict"),
            "pass_criterion_met": ha.get("pass_criterion_met"),
        }
    if HORIZON_EVAL_V2.is_file():
        he = _load_json(HORIZON_EVAL_V2)
        ie = he.get("sasang_intensity_eval") if isinstance(he.get("sasang_intensity_eval"), dict) else {}
        dec = (ie.get("variants") or {}).get("decoupled_psych_only") or {}
        out["kospi_intensity_role_eval"] = {
            "path": str(HORIZON_EVAL_V2),
            "legacy_spearman": ie.get("spearman_rank_corr"),
            "decoupled_psych_spearman": dec.get("spearman_rank_corr"),
            "mechanical_proxy_suspect": ie.get("mechanical_proxy_suspect"),
            "note": "KOSPI intensity role pass — external emotion rail only for promotion",
        }
    return out


def _pack0b_eval_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False}
    doc = _load_json(path)
    adapter = str(doc.get("adapter_path") or "")
    model = str(doc.get("model_name") or "")
    stale = "TinyLlama" in model or "run_pack0b_pipeline_latest" in adapter
    return {
        "path": str(path),
        "present": True,
        "stale_legacy": stale,
        "model_name": doc.get("model_name"),
        "adapter_path": doc.get("adapter_path"),
        "rows": doc.get("rows"),
        "parse_ok_rate": doc.get("parse_ok_rate"),
        "alignment_pass_rate_raw": doc.get("alignment_pass_rate"),
    }


def _build_pack0b_lora_rail() -> dict[str, Any]:
    out: dict[str, Any] = {
        "rail_id": "myeongni_pack0b_lora_v1_2",
        "eval_task": "Qwen Pack0-B LoRA locked_eval — isolated from KOSPI market verdict",
        "forbidden_in_market_verdict": True,
    }
    smoke = _pack0b_eval_summary(PACK0B_SMOKE_EVAL)
    final = _pack0b_eval_summary(PACK0B_FINAL_EVAL)
    out["smoke100_eval"] = smoke
    out["final_eval"] = final
    if PACK0B_WATCH.is_file():
        w = _load_json(PACK0B_WATCH)
        out["train_watch"] = {
            "path": str(PACK0B_WATCH),
            "phase": w.get("phase"),
            "last_step": w.get("last_step"),
            "max_steps": w.get("max_steps"),
            "resume_checkpoint": w.get("resume_checkpoint"),
            "adapter_dir": w.get("adapter_dir"),
            "train_alive": w.get("train_alive"),
        }
    parse_ok = float(smoke.get("parse_ok_rate") or 0.0) if smoke.get("present") and not smoke.get("stale_legacy") else 0.0
    out["contract_pass"] = bool(smoke.get("present") and not smoke.get("stale_legacy") and parse_ok >= 0.95)
    phase = (out.get("train_watch") or {}).get("phase")
    out["status"] = "training" if phase == "training" else ("eval_pending" if phase == "eval" else "idle_or_done")
    out["note"] = (
        "final_eval is stale until full500 Qwen adapter completes train+locked_eval; "
        "smoke100 parse_ok=1.0 is format gate only — alignment_pass still 0 on smoke."
    )
    return out


def _build_myeongni_weather_rail() -> dict[str, Any]:
    out: dict[str, Any] = {
        "rail_id": "myeongni_weather_prophecy_v1_2",
        "eval_task": "weather fusion profile + general_prophecy Brier + session/weather join SSOT",
    }

    if WEATHER_FUSION.is_file():
        fusion = _load_json(WEATHER_FUSION)
        rec = fusion.get("recommended") if isinstance(fusion.get("recommended"), dict) else {}
        out["weather_fusion_profile"] = {
            "path": str(WEATHER_FUSION),
            "weather_term": rec.get("weather_term"),
            "confidence_adjusted": rec.get("confidence_adjusted"),
            "direct_match_rate_or_coverage": (fusion.get("input") or {}).get("direct_match_rate_or_coverage"),
        }
    else:
        out["weather_fusion_profile"] = {"path": str(WEATHER_FUSION), "present": False}

    if PROMOTION_GATE.is_file():
        pg = _load_json(PROMOTION_GATE)
        checks = pg.get("stage_checks") if isinstance(pg.get("stage_checks"), dict) else {}
        out["myeongni_promotion_gate"] = {
            "path": str(PROMOTION_GATE),
            "weather_signal_linked": checks.get("weather_signal_linked"),
            "decision": pg.get("decision"),
        }

    if BRIER_EVAL.is_file():
        be = _load_json(BRIER_EVAL)
        m = be.get("metrics") if isinstance(be.get("metrics"), dict) else {}
        out["general_prophecy_brier_eval"] = {
            "path": str(BRIER_EVAL),
            "mean_brier_score": m.get("mean_brier_score"),
            "n_evaluated": m.get("n_evaluated"),
            "by_domain_tag": m.get("by_domain_tag"),
        }

    if HOLDOUT_REPORT.is_file():
        hr = _load_json(HOLDOUT_REPORT)
        cohorts = hr.get("cohorts") if isinstance(hr.get("cohorts"), dict) else {}
        out["explainability_holdout"] = {
            "path": str(HOLDOUT_REPORT),
            "brier_sanity_cohort": cohorts.get("brier_sanity"),
            "holdout_core_n": (hr.get("holdout_core") or {}).get("n_questions"),
        }

    join_meta = _latest_glob("reports/btrack_session_panel_wide_prophecy_weather_*.join.meta.json")
    if join_meta and join_meta.is_file():
        jm = _load_json(join_meta)
        out["session_weather_join_latest"] = {
            "path": str(join_meta),
            "counts": jm.get("counts"),
            "inputs": jm.get("inputs"),
        }

    if WEATHER_CORR_JSON.is_file():
        out["wide_correlation_json"] = {"path": str(WEATHER_CORR_JSON), "present": True}
    else:
        out["wide_correlation_json"] = {
            "path": str(WEATHER_CORR_JSON),
            "present": False,
            "note": "run Run-BtrackSessionPanelWeatherCorrChain_v1.ps1 for full-window refresh",
        }

    if FULL_WINDOW_FUSION.is_file():
        ff = _load_json(FULL_WINDOW_FUSION)
        ff_sum = ff.get("summary") if isinstance(ff.get("summary"), dict) else {}
        out["full_window_disaster_risk_fusion"] = {
            "path": str(FULL_WINDOW_FUSION),
            "n_days": ff_sum.get("n_days"),
            "grade_changes": ff_sum.get("grade_changes"),
            "wide_csv": (ff.get("inputs") or {}).get("wide_csv"),
            "note": "30y panel fusion (myeongni+weather+news); supplementary only — not KOSPI direction gate",
        }

    n_weather_pending = 0
    if REGISTRY.is_file():
        reg = _load_json(REGISTRY)
        questions = reg.get("questions") if isinstance(reg.get("questions"), list) else []
        weather_qs = [
            q
            for q in questions
            if isinstance(q, dict)
            and "weather" in [str(t).lower() for t in (q.get("domain_tags") or [])]
        ]
        n_weather_pending = sum(
            1
            for q in weather_qs
            if q.get("outcome_binary") is None and q.get("resolved_outcome_binary") is None
        )
        out["registry_weather_questions"] = {
            "path": str(REGISTRY),
            "n_weather_tagged": len(weather_qs),
            "n_pending_resolution": n_weather_pending,
        }

    brier = (out.get("general_prophecy_brier_eval") or {}).get("mean_brier_score")
    n_brier = (out.get("general_prophecy_brier_eval") or {}).get("n_evaluated")
    fusion_ok = bool((out.get("weather_fusion_profile") or {}).get("weather_term") is not None)
    gate_linked = (out.get("myeongni_promotion_gate") or {}).get("weather_signal_linked") is True
    brier_ok = isinstance(brier, (int, float)) and isinstance(n_brier, int) and n_brier >= 3 and float(brier) <= 0.25
    out["contract_pass"] = fusion_ok and (gate_linked or brier_ok)
    out["pass_components"] = {
        "fusion_profile_ok": fusion_ok,
        "promotion_weather_linked": gate_linked,
        "brier_eval_ok": brier_ok,
    }
    out["status"] = "ok" if out["contract_pass"] else "linked_partial"
    out["note"] = (
        "Uses trained weather fusion + prophecy Brier SSOT — not single pending KMA row alone. "
        "Full 30y panel weather corr: Run-BtrackSessionPanelWeatherCorrChain_v1.ps1 on full window."
    )
    return out


def _build_logos_chronology_rail() -> dict[str, Any]:
    out: dict[str, Any] = {
        "rail_id": "logos_chronology_era_v1_2",
        "eval_task": "historical era blind matching + hist holdout Brier",
    }
    if CHRONOLOGY.is_file():
        ch = _load_json(CHRONOLOGY)
        summary = ch.get("summary") if isinstance(ch.get("summary"), dict) else {}
        out["chronology_blind_eval"] = {
            "path": str(CHRONOLOGY),
            "n_events": summary.get("n_events"),
            "hit_at_1_strict": summary.get("hit_at_1_strict"),
            "hit_at_1_relaxed": summary.get("hit_at_1_relaxed"),
            "hit_at_3": summary.get("hit_at_3"),
            "tag_mode": summary.get("tag_mode"),
        }
    else:
        out["chronology_blind_eval"] = {"path": str(CHRONOLOGY), "present": False}

    if HIST_BRIER.is_file():
        hb = _load_json(HIST_BRIER)
        prod = hb.get("production_hist_only") if isinstance(hb.get("production_hist_only"), dict) else {}
        out["historical_holdout_brier"] = {
            "path": str(HIST_BRIER),
            "n_evaluated": prod.get("n_evaluated"),
            "mean_brier_score": prod.get("mean_brier_score"),
        }
    else:
        out["historical_holdout_brier"] = {"path": str(HIST_BRIER), "present": False}

    hit_relaxed = (out.get("chronology_blind_eval") or {}).get("hit_at_1_relaxed")
    hist_brier = (out.get("historical_holdout_brier") or {}).get("mean_brier_score")
    chrono_pass = isinstance(hit_relaxed, (int, float)) and float(hit_relaxed) >= 0.08
    brier_pass = isinstance(hist_brier, (int, float)) and float(hist_brier) <= 0.45
    out["contract_pass"] = chrono_pass and brier_pass if hit_relaxed is not None and hist_brier is not None else None
    out["pass_components"] = {"chronology_hit_relaxed_ok": chrono_pass, "hist_brier_ok": brier_pass}
    out["status"] = "ok" if out.get("contract_pass") is not None else "partial_artifacts"
    out["note"] = "[NON_GATING] Logos chronology — not merged into KOSPI daily verdict"
    return out


def build_supplementary_rails() -> dict[str, Any]:
    sasang = _build_sasang_sentiment_rail()
    myeongni = _build_myeongni_weather_rail()
    logos = _build_logos_chronology_rail()
    pack0b = _build_pack0b_lora_rail()

    passes = [
        k
        for k, v in (("sasang", sasang), ("myeongni", myeongni), ("logos", logos))
        if v.get("contract_pass") is True
    ]

    return {
        "schema": "lens_sovereignty_supplementary_rails_v1_2",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "RESEARCH_ONLY_HYPO_B",
        "ops_model": "batch_ssot_refresh",
        "forbidden_in_daily_kospi_verdict": True,
        "rails": {
            "sasang_sentiment": sasang,
            "myeongni_weather_prophecy": myeongni,
            "logos_chronology": logos,
            "pack0b_lora": pack0b,
        },
        "supplementary_verdict": (
            "SUPP_ALIGNED"
            if len(passes) >= 2
            else "SUPP_PARTIAL"
            if len(passes) == 1
            else "SUPP_FAIL"
        ),
        "supplementary_passes": passes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_supplementary_rails()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "supplementary_verdict": doc["supplementary_verdict"],
                "passes": doc["supplementary_passes"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
