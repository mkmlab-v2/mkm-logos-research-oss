#!/usr/bin/env python3
"""Build parallel micro-signal observation bundle from existing B-track artifacts.

Ingests market OHLCV score tail, myeongri/logos response v2, sasang lens, and
optional general_prophecy weather-tagged forecasts. No cross-lens fusion.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "micro_signal_observation_bundle_v1_latest.json"
DEFAULT_BRIEF = ROOT / "docs" / "final" / "artifacts" / "micro_signal_observation_brief_v1_latest.md"

SCORE = ROOT / "reports" / "btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_response_v2_latest.json"
LOGOS = ROOT / "docs" / "final" / "artifacts" / "mkm_logos_response_v2_latest.json"
SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
GENERAL = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
SCIENCE = ROOT / "docs" / "final" / "artifacts" / "science_core_slice_2026h1_market_sasang_v1_latest.json"

EXPECTED_DOMAINS = [
    "market_ohlcv",
    "weather_env",
    "myeongni_time",
    "sasang_constitution",
    "logos_text",
    "science_core",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _gov(*, non_gating: bool = False) -> dict[str, Any]:
    return {
        "research_only": True,
        "non_gating": non_gating,
        "a_track_autobind_forbidden": True,
    }


def _row(
    *,
    observation_id: str,
    domain: str,
    lens_id: str,
    signal_kind: str,
    observed_at_utc: str,
    provenance: dict[str, Any],
    magnitude_0_1: float | None = None,
    signed_delta: float | None = None,
    confidence_0_1: float | None = None,
    precursor_hint: str | None = None,
    instrument: str | None = None,
    note: str | None = None,
    non_gating: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": "micro_signal_observation_row_v1",
        "observation_id": observation_id,
        "domain": domain,
        "lens_id": lens_id,
        "signal_kind": signal_kind,
        "observed_at_utc": observed_at_utc,
        "provenance": provenance,
        "governance": _gov(non_gating=non_gating),
    }
    if magnitude_0_1 is not None:
        out["magnitude_0_1"] = round(_clamp01(magnitude_0_1), 6)
    if signed_delta is not None:
        out["signed_delta_-1_1"] = round(max(-1.0, min(1.0, signed_delta)), 6)
    if confidence_0_1 is not None:
        out["confidence_0_1"] = round(_clamp01(confidence_0_1), 6)
    if precursor_hint:
        out["precursor_hint"] = precursor_hint
    if instrument:
        out["instrument"] = instrument
    if note:
        out["note"] = note
    return out


def _market_rows(score_path: Path) -> list[dict[str, Any]]:
    doc = _read_json(score_path)
    if not doc or not isinstance(doc.get("rows"), list):
        return []
    rows = [r for r in doc["rows"] if isinstance(r, dict)]
    out: list[dict[str, Any]] = []
    gen = str(doc.get("generated_at_utc") or _utc_now())
    ref = str(score_path.relative_to(ROOT)) if score_path.is_relative_to(ROOT) else str(score_path)
    for instrument in ("kospi", "btc"):
        inst_rows = [r for r in rows if r.get("instrument") == instrument]
        if not inst_rows:
            continue
        tail = inst_rows[-3:]
        abs_rets = [abs(float(r.get("daily_return") or 0.0)) for r in tail]
        micro_vol = sum(abs_rets) / len(abs_rets) if abs_rets else 0.0
        last = tail[-1]
        daily_ret = float(last.get("daily_return") or 0.0)
        pred = str(last.get("predicted_direction") or "neutral")
        hint_map = {"bull": "bull", "bear": "bear", "neutral": "neutral"}
        eval_date = str(last.get("eval_date") or doc.get("eval_date") or "unknown")
        out.append(
            _row(
                observation_id=f"market_ohlcv.micro_vol.{instrument}.{eval_date.replace('-', '')}",
                domain="market_ohlcv",
                lens_id="field",
                signal_kind="micro_volatility_3d",
                observed_at_utc=gen,
                magnitude_0_1=min(micro_vol * 12.0, 1.0),
                signed_delta=max(-1.0, min(1.0, daily_ret * 8.0)),
                confidence_0_1=0.55,
                precursor_hint=hint_map.get(pred, "watch"),
                instrument=instrument,
                provenance={
                    "source_kind": "artifact_json",
                    "ref": ref,
                    "note": "tail-3 abs(daily_return) mean; last row direction as hint",
                    "source_generated_at_utc": gen,
                },
            )
        )
    return out


def _myeongni_rows(path: Path) -> list[dict[str, Any]]:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "mkm_myeongni_response_v2":
        return []
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    final = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
    gen = str(doc.get("generated_at_utc") or _utc_now())
    ref = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    decision = str(final.get("decision") or "WATCH").upper()
    hint = "watch" if decision == "WATCH" else "neutral"
    return [
        _row(
            observation_id=f"myeongni_time.jijangan_pressure.{gen[:10].replace('-', '')}",
            domain="myeongni_time",
            lens_id="myeongni",
            signal_kind="jijangan_pressure",
            observed_at_utc=gen,
            magnitude_0_1=float(core.get("jijangan_pressure") or 0.0),
            signed_delta=float(core.get("direction_core") or 0.0),
            confidence_0_1=float(coord.get("confidence_adjusted") or core.get("confidence_core") or 0.0),
            precursor_hint=hint,
            provenance={
                "source_kind": "artifact_json",
                "ref": ref,
                "note": "mkm_myeongni_response_v2 core_layer",
                "source_generated_at_utc": gen,
            },
        ),
        _row(
            observation_id=f"myeongni_time.school_disagreement.{gen[:10].replace('-', '')}",
            domain="myeongni_time",
            lens_id="myeongni",
            signal_kind="school_disagreement_index",
            observed_at_utc=gen,
            magnitude_0_1=float(core.get("school_disagreement_index") or 0.0),
            signed_delta=float(core.get("ten_god_balance") or 0.0),
            confidence_0_1=float(core.get("confidence_core") or 0.0),
            precursor_hint="phase_transition" if float(core.get("school_disagreement_index") or 0.0) > 0.45 else "neutral",
            provenance={
                "source_kind": "artifact_json",
                "ref": ref,
                "note": "myeongri intra-school micro-tension",
                "source_generated_at_utc": gen,
            },
        ),
    ]


def _logos_rows(path: Path) -> list[dict[str, Any]]:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "mkm_logos_response_v2":
        return []
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    gen = str(doc.get("generated_at_utc") or _utc_now())
    ref = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    signal = str(core.get("signal_core") or "HOLD").upper()
    hint = "hold" if signal == "HOLD" else "watch"
    return [
        _row(
            observation_id=f"logos_text.archetype_resonance.{gen[:10].replace('-', '')}",
            domain="logos_text",
            lens_id="logos",
            signal_kind="archetype_resonance",
            observed_at_utc=gen,
            magnitude_0_1=float(core.get("archetype_resonance") or 0.0),
            signed_delta=float(core.get("direction_core") or 0.0),
            confidence_0_1=float(coord.get("confidence_adjusted") or core.get("confidence_core") or 0.0),
            precursor_hint=hint,
            provenance={
                "source_kind": "artifact_json",
                "ref": ref,
                "note": "mkm_logos_response_v2; NON_GATING assistive text morphology layer",
                "source_generated_at_utc": gen,
            },
            non_gating=True,
            note="Logos lens is assistive only; must not gate Track A or live.",
        )
    ]


def _sasang_rows(path: Path) -> list[dict[str, Any]]:
    doc = _read_json(path)
    if not doc:
        return []
    gen = str(doc.get("ts_utc") or _utc_now())
    ref = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    stream = doc.get("sasang_stream_outputs") if isinstance(doc.get("sasang_stream_outputs"), dict) else {}
    mr = stream.get("machine_readables") if isinstance(stream.get("machine_readables"), dict) else {}
    axis = doc.get("b_track_axis_scores_v1") if isinstance(doc.get("b_track_axis_scores_v1"), dict) else {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    regime = str(stream.get("regime_hypothesis") or "unknown")
    hint = "phase_transition" if regime == "phase_transition" else str(stream.get("mapping_target") or "neutral")
    return [
        _row(
            observation_id=f"sasang_constitution.thermal_imbalance.{gen[:10].replace('-', '')}",
            domain="sasang_constitution",
            lens_id="sasang",
            signal_kind="thermal_imbalance_proxy",
            observed_at_utc=gen,
            magnitude_0_1=abs(float(axis.get("thermal_imbalance_proxy") or scores.get("direction_score") or 0.0)),
            signed_delta=float(axis.get("thermal_imbalance_proxy") or scores.get("direction_score") or 0.0),
            confidence_0_1=float(scores.get("confidence") or 0.0),
            precursor_hint=hint if hint in {"bull", "bear", "neutral", "sideways", "watch", "hold", "phase_transition"} else "unknown",
            provenance={
                "source_kind": "artifact_json",
                "ref": ref,
                "note": "sasang_independent_lens machine_readables; not clinical diagnosis",
                "source_generated_at_utc": gen,
            },
            note=str(stream.get("rationale") or "")[:240] or None,
        ),
        _row(
            observation_id=f"sasang_constitution.vol_rarefaction.{gen[:10].replace('-', '')}",
            domain="sasang_constitution",
            lens_id="sasang",
            signal_kind="volatility_rarefaction_proxy",
            observed_at_utc=gen,
            magnitude_0_1=float(mr.get("volatility_rarefaction_proxy") or 0.0),
            signed_delta=float(mr.get("heat_proxy") or 0.0) - float(mr.get("cold_proxy") or 0.0),
            confidence_0_1=float(scores.get("confidence") or 0.0),
            precursor_hint="phase_transition",
            provenance={
                "source_kind": "artifact_json",
                "ref": ref,
                "note": "heat/cold/vol rarefaction micro-proxies",
                "source_generated_at_utc": gen,
            },
        ),
    ]


def _weather_rows(path: Path) -> list[dict[str, Any]]:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "general_prophecy_registry_v1":
        return []
    gen = str(doc.get("generated_at_utc") or _utc_now())
    ref = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    out: list[dict[str, Any]] = []
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        tags = {str(t).lower() for t in (q.get("domain_tags") or [])}
        if not (tags & {"weather", "climate", "meteo", "environment"}):
            continue
        qid = str(q.get("question_id") or "weather")
        fc = q.get("forecasts") or []
        if not isinstance(fc, list) or not fc:
            continue
        last = fc[-1] if isinstance(fc[-1], dict) else {}
        p = float(last.get("probability_0_1") or 0.5)
        out.append(
            _row(
                observation_id=f"weather_env.forecast_slot.{qid}",
                domain="weather_env",
                lens_id="field",
                signal_kind="general_prophecy_forecast_probability",
                observed_at_utc=gen,
                magnitude_0_1=abs(p - 0.5) * 2.0,
                signed_delta=(p - 0.5) * 2.0,
                confidence_0_1=0.5,
                precursor_hint="bull" if p >= 0.6 else "bear" if p <= 0.4 else "neutral",
                provenance={
                    "source_kind": "artifact_json",
                    "ref": ref,
                    "note": f"general_prophecy question_id={qid}",
                    "source_generated_at_utc": gen,
                },
            )
        )
    return out


def _science_rows(path: Path) -> list[dict[str, Any]]:
    doc = _read_json(path)
    if not doc or doc.get("schema") != "science_core_long_history_slice_eval_bundle_v1":
        return []
    gen = str(doc.get("generated_at_utc") or _utc_now())
    ref = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    out: list[dict[str, Any]] = []
    legs = doc.get("legs") if isinstance(doc.get("legs"), dict) else {}
    for leg_name, leg in legs.items():
        if not isinstance(leg, dict):
            continue
        slices = leg.get("slices") if isinstance(leg.get("slices"), dict) else {}
        by_year = slices.get("by_year") if isinstance(slices.get("by_year"), dict) else {}
        for year, ydoc in by_year.items():
            if not isinstance(ydoc, dict):
                continue
            lenses = ydoc.get("lenses") if isinstance(ydoc.get("lenses"), dict) else {}
            sc = lenses.get("science_core") if isinstance(lenses.get("science_core"), dict) else {}
            if not sc:
                continue
            hit = float(sc.get("directional_hit_rate") or 0.0)
            out.append(
                _row(
                    observation_id=f"science_core.directional_hit.{leg_name}.{year}",
                    domain="science_core",
                    lens_id="science",
                    signal_kind="directional_hit_rate_slice",
                    observed_at_utc=gen,
                    magnitude_0_1=abs(hit - 0.5) * 2.0,
                    signed_delta=(hit - 0.5) * 2.0,
                    confidence_0_1=0.45,
                    precursor_hint="watch",
                    instrument=str(leg.get("instrument") or leg_name),
                    provenance={
                        "source_kind": "artifact_json",
                        "ref": ref,
                        "note": f"science_core slice year={year}; research_only calibration",
                        "source_generated_at_utc": gen,
                    },
                )
            )
    return out[:2]


def build_bundle(
    *,
    score_path: Path = SCORE,
    myeongni_path: Path = MYEONGNI,
    logos_path: Path = LOGOS,
    sasang_path: Path = SASANG,
    general_path: Path = GENERAL,
    science_path: Path = SCIENCE,
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    observations.extend(_market_rows(score_path))
    observations.extend(_weather_rows(general_path))
    observations.extend(_myeongni_rows(myeongni_path))
    observations.extend(_sasang_rows(sasang_path))
    observations.extend(_logos_rows(logos_path))
    observations.extend(_science_rows(science_path))

    if not observations:
        raise RuntimeError("no observations extracted; check input artifact paths")

    present = sorted({str(o["domain"]) for o in observations})
    missing = [d for d in EXPECTED_DOMAINS if d not in present]

    return {
        "schema": "micro_signal_observation_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": True,
        "lens_partition_ack": True,
        "fusion_forbidden_ack": True,
        "observations": observations,
        "summary": {
            "n_observations": len(observations),
            "domains_present": present,
            "domains_missing": missing,
            "expected_domains": list(EXPECTED_DOMAINS),
        },
    }


def _brief_md(bundle: dict[str, Any]) -> str:
    lines = [
        "# Micro-signal observation brief (B-track)",
        "",
        f"- generated_at_utc: `{bundle.get('generated_at_utc')}`",
        f"- n_observations: `{bundle['summary']['n_observations']}`",
        f"- domains_present: `{', '.join(bundle['summary']['domains_present'])}`",
        f"- domains_missing: `{', '.join(bundle['summary']['domains_missing']) or '(none)'}`",
        "",
        "## Parallel rows (no fusion)",
        "",
    ]
    for o in bundle.get("observations") or []:
        if not isinstance(o, dict):
            continue
        mag = o.get("magnitude_0_1")
        sd = o.get("signed_delta_-1_1")
        conf = o.get("confidence_0_1")
        lines.append(
            f"- **{o.get('observation_id')}** · domain=`{o.get('domain')}` · "
            f"signal=`{o.get('signal_kind')}` · mag={mag} · delta={sd} · conf={conf} · "
            f"hint=`{o.get('precursor_hint', '—')}`"
        )
    lines.extend(
        [
            "",
            "---",
            "*Creative-Lock / [HYPO] / research_only. Parallel observations only; lens partition preserved.*",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--brief", type=Path, default=DEFAULT_BRIEF)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--skip-brief", action="store_true")
    ap.add_argument("--score-json", type=Path, default=SCORE)
    ap.add_argument("--myeongni-json", type=Path, default=MYEONGNI)
    ap.add_argument("--logos-json", type=Path, default=LOGOS)
    ap.add_argument("--sasang-json", type=Path, default=SASANG)
    ap.add_argument("--general-prophecy-json", type=Path, default=GENERAL)
    ap.add_argument("--science-json", type=Path, default=SCIENCE)
    ns = ap.parse_args()

    try:
        bundle = build_bundle(
            score_path=ns.score_json,
            myeongni_path=ns.myeongni_json,
            logos_path=ns.logos_json,
            sasang_path=ns.sasang_json,
            general_path=ns.general_prophecy_json,
            science_path=ns.science_json,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    if ns.stdout_only:
        sys.stdout.write(payload)
        return 0

    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(payload + "\n", encoding="utf-8")
    print(str(ns.output.resolve()))

    if not ns.skip_brief:
        ns.brief.parent.mkdir(parents=True, exist_ok=True)
        ns.brief.write_text(_brief_md(bundle), encoding="utf-8")
        print(str(ns.brief.resolve()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
