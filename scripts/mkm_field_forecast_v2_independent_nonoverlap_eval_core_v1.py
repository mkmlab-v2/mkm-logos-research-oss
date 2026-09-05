#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Field Forecast V2 independent non-overlap evaluation core (research_only).

Evaluates FROZEN DEV Field forecast on a preregistered non-overlap window.
CORE_RULE: evaluate frozen system; do not improve frozen system.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from scripts.mkm_field_forecast_v2_dev_smoke_walkforward_core_v1 import (  # noqa: E402
    CLASSES,
    HORIZONS,
    build_dev_row,
    build_walk_forward_folds,
)
from scripts.mkm_field_forecast_v2_dev_broader_panel_independent_requal_core_v1 import (  # noqa: E402
    BOOT_N,
    QUAL_ENUM,
    _bootstrap_mcc_ci,
    _equal_coverage_always_up,
    _majority,
    _permutation_mcc_null,
    _qualify,
)
from scripts.mkm_field_stock_forecast_v2_phase2_core_v1 import (  # noqa: E402
    compute_metrics,
    load_ohlcv_closes,
)

ACK_PATH = ROOT / "docs/final/artifacts/commander_field_forecast_v2_independent_nonoverlap_eval_ack_v1.json"
ACK_TOKEN = "COMMANDER_FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_ACK"
PASS_CEILING = "INDEPENDENT_NONOVERLAP_QUALIFICATION_ONLY"
EVIDENCE_CEILING = "INDEPENDENT_NONOVERLAP_QUALIFICATION_ONLY"
DECIDE_OK = "FIELD_FORECAST_V2_INDEPENDENT_NONOVERLAP_EVAL_STRUCTURAL_OK"
CORE_RULE = "evaluate frozen system; do not improve frozen system"

REFREEZE_MANIFEST = (
    ROOT / "docs/final/artifacts/mkm_field_forecast_v2_dev_phase2_equivalent_refreeze_manifest_latest.json"
)
REFREEZE_HASHES = (
    ROOT / "docs/final/artifacts/mkm_field_forecast_v2_dev_phase2_equivalent_refreeze_hashes_latest.json"
)
REFREEZE_UNIVERSE = (
    ROOT
    / "docs/final/artifacts/mkm_field_forecast_v2_dev_phase2_equivalent_refreeze_universe_date_window_manifest_latest.json"
)
REFREEZE_CHECK = (
    ROOT / "docs/final/artifacts/mkm_field_forecast_v2_dev_phase2_equivalent_refreeze_check_v1_latest.json"
)
DEV_BROADER_CONFIG = ROOT / "docs/final/artifacts/mkm_field_forecast_v2_dev_broader_panel_config_latest.json"
DEV_BROADER_SUMMARY = (
    ROOT / "docs/final/artifacts/mkm_field_forecast_v2_dev_broader_panel_independent_requal_latest.json"
)
PHASE2_PRED = ROOT / "reports/mkm_field_stock_forecast_v2_phase2_prediction_raw_latest.jsonl"
REQUAL_PRED = ROOT / "reports/mkm_field_forecast_v2_dev_independent_requal_prediction_raw_latest.jsonl"
SMOKE_PRED = ROOT / "reports/mkm_field_forecast_v2_dev_smoke_prediction_raw_latest.jsonl"
MACRO_AUDIT = ROOT / "reports/science_core_macro_gate_bias_audit_v1_latest.json"

EXPECTED_UNIVERSE = ["KOSPI", "066570", "005930", "000660", "064350"]
SEED = 20260904
BASELINE_NAMES = (
    "majority_class",
    "always_up",
    "always_neutral",
    "previous_direction",
    "simple_momentum",
    "market_only",
    "price_only",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _git_sha(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0:
            return (r.stdout or "").strip() or "UNKNOWN"
    except OSError:
        pass
    return "UNKNOWN"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _ranges_overlap(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return not (a_end < b_start or b_end < a_start)


def _asof_set_from_jsonl(path: Path, keys: tuple[str, ...]) -> set[str]:
    out: set[str] = set()
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            for k in keys:
                v = o.get(k)
                if v:
                    out.add(str(v)[:10])
                    break
    return out


def collect_prior_windows(root: Path) -> dict[str, Any]:
    broader = _load(DEV_BROADER_SUMMARY) if DEV_BROADER_SUMMARY.is_file() else {}
    wm = broader.get("window_meta") or {}
    uni = _load(REFREEZE_UNIVERSE) if REFREEZE_UNIVERSE.is_file() else {}
    reserved = uni.get("reserved_future_unseen") or {
        "date_start_inclusive": "2026-09-03",
        "date_end_inclusive": None,
    }
    phase2_asofs = _asof_set_from_jsonl(PHASE2_PRED, ("asof",))
    requal_asofs = _asof_set_from_jsonl(REQUAL_PRED, ("asof_date", "asof"))
    smoke_asofs = _asof_set_from_jsonl(SMOKE_PRED, ("asof_date", "asof"))
    return {
        "requal_window": {
            "id": "dev_independent_requal",
            "date_start": wm.get("date_start"),
            "date_end": wm.get("date_end"),
            "n_bars": wm.get("n_bars"),
        },
        "smoke_window": {
            "id": "dev_smoke_tail",
            "date_start": wm.get("smoke_tail_date_start"),
            "date_end": wm.get("smoke_tail_date_end"),
            "n_bars": 160,
        },
        "reserved_future": reserved,
        "phase2_oos": {
            "id": "phase2_oos_asof",
            "date_start": min(phase2_asofs) if phase2_asofs else None,
            "date_end": max(phase2_asofs) if phase2_asofs else None,
            "n_unique_asof": len(phase2_asofs),
        },
        "phase2_asofs": phase2_asofs,
        "requal_asofs": requal_asofs,
        "smoke_asofs": smoke_asofs,
        "used_asofs": phase2_asofs | requal_asofs | smoke_asofs,
    }


def select_nonoverlap_window(
    all_days: list[str], prior: dict[str, Any]
) -> tuple[list[str], dict[str, Any]]:
    used = set(prior.get("used_asofs") or set())
    reserved = prior.get("reserved_future") or {}
    reserved_start = str(reserved.get("date_start_inclusive") or "2026-09-03")
    reserved_end = reserved.get("date_end_inclusive")
    reserved_end_s = str(reserved_end) if reserved_end else None
    reserved_pool = [
        d
        for d in all_days
        if d >= reserved_start and (reserved_end_s is None or d <= reserved_end_s)
    ]
    unused = [d for d in reserved_pool if d not in used]
    meta: dict[str, Any] = {
        "selection_rule": "reserved_future_unseen_only_no_historical_backfill",
        "reserved_future_date_start": reserved_start,
        "reserved_future_date_end": reserved_end_s,
        "reserved_future_available_bars": len(reserved_pool),
        "n_unused_asof_days": len(unused),
        "locked_before_metrics": True,
        "historical_unused_backfill_forbidden": True,
        "smoke_reuse_forbidden": True,
    }
    if not unused:
        meta.update(
            {
                "window_label": "independent_nonoverlap_reserved_future",
                "date_start": reserved_start,
                "date_end": reserved_end_s or (reserved_pool[-1] if reserved_pool else None),
                "n_bars": 0,
                "insufficient_reason": "reserved_future_unseen_empty_or_consumed",
                "note_ko": "예약 unseen(2026-09-03~)만. 과거 미사용 구간 편입 금지. 창이 비면 INSUFFICIENT_DATA.",
            }
        )
        return [], meta
    idx = {d: i for i, d in enumerate(all_days)}
    segs: list[tuple[str, str, int]] = []
    start = prev = unused[0]
    for d in unused[1:]:
        if idx[d] == idx[prev] + 1:
            prev = d
        else:
            segs.append((start, prev, idx[prev] - idx[start] + 1))
            start = prev = d
    segs.append((start, prev, idx[prev] - idx[start] + 1))
    best = max(segs, key=lambda x: x[2])
    days = [d for d in unused if best[0] <= d <= best[1]]
    meta.update(
        {
            "window_label": "independent_nonoverlap_reserved_future",
            "date_start": best[0],
            "date_end": best[1],
            "n_bars": len(days),
            "segments_all": [{"start": a, "end": b, "n": n} for a, b, n in segs],
            "note_ko": "예약 unseen(2026-09-03~)만. Phase2 OOS·DEV requal·smoke asof 교집합 0. 과거 미사용 편입 금지.",
        }
    )
    return days, meta


def build_nonoverlap_proof(
    window_meta: dict[str, Any], prior: dict[str, Any], eval_days: list[str]
) -> dict[str, Any]:
    eval_set = set(eval_days)
    checks: list[dict[str, Any]] = []

    def add(code: str, ok: bool, detail: str = "") -> None:
        checks.append({"ok": ok, "code": code, "detail": detail})

    for name, aset in (
        ("phase2_oos", prior.get("phase2_asofs") or set()),
        ("requal", prior.get("requal_asofs") or set()),
        ("smoke", prior.get("smoke_asofs") or set()),
    ):
        inter = eval_set & set(aset)
        add(f"NO_ASOF_OVERLAP_{name.upper()}", len(inter) == 0, f"n_intersect={len(inter)}")
    rq = prior.get("requal_window") or {}
    sm = prior.get("smoke_window") or {}
    p2 = prior.get("phase2_oos") or {}
    ds, de = window_meta.get("date_start"), window_meta.get("date_end")
    if ds and de and rq.get("date_start") and rq.get("date_end"):
        add(
            "NO_RANGE_OVERLAP_REQUAL",
            not _ranges_overlap(str(ds), str(de), str(rq["date_start"]), str(rq["date_end"])),
        )
    if ds and de and sm.get("date_start") and sm.get("date_end"):
        add(
            "NO_RANGE_OVERLAP_SMOKE",
            not _ranges_overlap(str(ds), str(de), str(sm["date_start"]), str(sm["date_end"])),
        )
    if ds and de and p2.get("date_start") and p2.get("date_end"):
        add(
            "NO_RANGE_OVERLAP_PHASE2_OOS",
            not _ranges_overlap(str(ds), str(de), str(p2["date_start"]), str(p2["date_end"])),
        )
    reserved_start = str(
        (prior.get("reserved_future") or {}).get("date_start_inclusive") or "2026-09-03"
    )
    add(
        "RESERVED_FUTURE_STATUS",
        True,
        f"reserved_start={reserved_start} available_bars={window_meta.get('reserved_future_available_bars')}",
    )
    add(
        "RESERVED_FUTURE_ONLY",
        (not eval_days) or all(str(d) >= reserved_start for d in eval_days),
        f"n_eval={len(eval_days)} min={min(eval_days) if eval_days else None}",
    )
    add(
        "NO_HISTORICAL_UNUSED_BACKFILL",
        window_meta.get("selection_rule") == "reserved_future_unseen_only_no_historical_backfill",
        str(window_meta.get("selection_rule")),
    )
    add(
        "WINDOW_LABEL_RESERVED_FUTURE",
        str(window_meta.get("window_label") or "") == "independent_nonoverlap_reserved_future",
        str(window_meta.get("window_label")),
    )
    ok = all(c["ok"] for c in checks)
    return {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_proof_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "eval_window": {
            "label": window_meta.get("window_label"),
            "date_start": ds,
            "date_end": de,
            "n_bars": window_meta.get("n_bars"),
        },
        "prior_windows": {
            "requal": rq,
            "smoke": sm,
            "phase2_oos": p2,
            "reserved_future": prior.get("reserved_future"),
        },
        "checks": checks,
        "fail_n": sum(1 for c in checks if not c["ok"]),
        "research_only": True,
    }


def verify_frozen_inputs(root: Path) -> dict[str, Any]:
    missing = [
        str(p)
        for p in (
            REFREEZE_MANIFEST,
            REFREEZE_HASHES,
            REFREEZE_UNIVERSE,
            REFREEZE_CHECK,
            DEV_BROADER_CONFIG,
        )
        if not p.is_file()
    ]
    if missing:
        return {"ok": False, "error": "FROZEN_INPUT_MISSING", "missing": missing}
    man = _load(REFREEZE_MANIFEST)
    hashes = _load(REFREEZE_HASHES)
    chk = _load(REFREEZE_CHECK)
    cfg = _load(DEV_BROADER_CONFIG)
    checks: list[dict[str, Any]] = []

    def add(code: str, ok: bool, detail: str = "") -> None:
        checks.append({"ok": ok, "code": code, "detail": detail})

    add("REFREEZE_CHECK_OK", chk.get("ok") is True, str(chk.get("DECIDE_ONE")))
    add(
        "UNIVERSE_EXACT",
        list(man.get("instrument_universe") or []) == EXPECTED_UNIVERSE,
        str(man.get("instrument_universe")),
    )
    add("HORIZONS_FROZEN", list(man.get("horizons") or []) == ["1d", "5d", "21d"])
    add("INCLUDES_3_LENS_FALSE", man.get("includes_3_lens") is False)
    cfg_sha = _sha256_bytes(
        json.dumps(cfg, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    expected_cfg = hashes.get("config_sha256")
    add("CONFIG_SHA256_MATCH", bool(expected_cfg) and cfg_sha == expected_cfg, cfg_sha)
    live_man_sha = _sha256_file(REFREEZE_MANIFEST)
    add("MANIFEST_HASH_PRESENT", live_man_sha is not None, live_man_sha or "")
    add("NO_CALL_FROZEN_PRESENT", bool(man.get("NO_CALL")))
    add("SCORES_THRESHOLDS_FROZEN_PRESENT", bool(man.get("scores_thresholds")))
    ok = all(c["ok"] for c in checks)
    return {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_frozen_input_hash_verify_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "checks": checks,
        "fail_n": sum(1 for c in checks if not c["ok"]),
        "refreeze_manifest_sha256": live_man_sha,
        "config_sha256": cfg_sha,
        "expected_config_sha256": expected_cfg,
        "instrument_universe": list(man.get("instrument_universe") or []),
        "horizons": list(man.get("horizons") or []),
        "NO_CALL": man.get("NO_CALL"),
        "scores_thresholds": man.get("scores_thresholds"),
        "baselines_frozen_from_refreeze": man.get("baselines"),
        "freeze_edits_forbidden": True,
        "research_only": True,
    }


def _price_only_action(mom: float | None, up_cut: float, down_cut: float) -> str:
    if mom is None:
        return "FLAT"
    score = max(-1.0, min(1.0, mom / 0.03))
    if score >= up_cut:
        return "UP"
    if score <= down_cut:
        return "DOWN"
    return "FLAT"


def _per_class_pr(rows: list[dict[str, Any]]) -> dict[str, Any]:
    called = [r for r in rows if r.get("pred_field") in CLASSES and r.get("y_sign") in CLASSES]
    out: dict[str, Any] = {}
    for c in CLASSES:
        tp = sum(1 for r in called if r["pred_field"] == c and r["y_sign"] == c)
        fp = sum(1 for r in called if r["pred_field"] == c and r["y_sign"] != c)
        fn = sum(1 for r in called if r["pred_field"] != c and r["y_sign"] == c)
        out[c] = {
            "precision": (tp / (tp + fp)) if (tp + fp) else None,
            "recall": (tp / (tp + fn)) if (tp + fn) else None,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return out


def run_independent_nonoverlap_eval(root: Path = ROOT) -> dict[str, Any]:
    freeze_verify = verify_frozen_inputs(root)
    if not freeze_verify.get("ok"):
        return {"ok": False, "error": "FROZEN_INPUT_VERIFY_FAIL", "freeze_verify": freeze_verify}

    cfg = json.loads(json.dumps(_load(DEV_BROADER_CONFIG)))
    prior = collect_prior_windows(root)
    kospi_closes = load_ohlcv_closes(root / cfg["universe"]["benchmark_csv"])
    kospi_all = sorted(kospi_closes.keys())
    eval_days, window_meta = select_nonoverlap_window(kospi_all, prior)
    proof = build_nonoverlap_proof(window_meta, prior, eval_days)
    if not proof.get("ok"):
        return {
            "ok": False,
            "error": "NON_OVERLAP_PROOF_FAIL",
            "window_meta": window_meta,
            "nonoverlap_proof": proof,
            "freeze_verify": freeze_verify,
        }

    prereg = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_prereg_manifest_v1",
        "generated_at_utc": _utc(),
        "locked_before_run": True,
        "locked_before_metrics": True,
        "CORE_RULE": CORE_RULE,
        "EVIDENCE_CEILING": EVIDENCE_CEILING,
        "pass_ceiling": PASS_CEILING,
        "research_only": True,
        "send_gate": "HOLD",
        "live": False,
        "AUTO_NEXT": False,
        "on_pass": "STOP",
        "on_signal_candidate": "STOP",
        "on_no_signal": "STOP",
        "instrument_universe_exact": EXPECTED_UNIVERSE,
        "horizons": list(HORIZONS),
        "window": window_meta,
        "prior_windows_cited": {
            "requal": prior.get("requal_window"),
            "smoke": prior.get("smoke_window"),
            "phase2_oos": prior.get("phase2_oos"),
            "reserved_future": prior.get("reserved_future"),
        },
        "freeze_guard": {
            "feature_weight_threshold_NO_CALL_edits": False,
            "horizon_change": False,
            "instrument_drop_cherry_pick": False,
            "best_regime_selection": False,
            "post_result_retune": False,
        },
        "lens_wall": {"sasang": False, "myeongni": False, "logos": False, "three_lens": False},
        "baselines": list(BASELINE_NAMES),
        "SIGNAL_CANDIDATE_NE_MARKET_ALPHA": True,
        "MARKET_ALPHA_claim_authorized": False,
    }

    macro = _load(MACRO_AUDIT) if MACRO_AUDIT.is_file() else {}
    macro_flags = list(macro.get("bias_flags") or [])
    macro_low_entropy = "low_macro_score_entropy" in macro_flags

    instruments_rows: dict[str, list[Any]] = {}
    panel_status: list[dict[str, Any]] = []
    for spec in cfg["universe"]["panel"]:
        csv_path = root / spec["csv"]
        entry: dict[str, Any] = {
            "id": spec["id"],
            "display": spec["display"],
            "model_family": spec["model_family"],
            "csv": spec["csv"],
            "available": csv_path.is_file(),
        }
        if not csv_path.is_file():
            entry["status"] = "MISSING"
            panel_status.append(entry)
            continue
        closes = load_ohlcv_closes(csv_path)
        if spec["model_family"] == "KOSPI_INDEX":
            days = eval_days
            rows = []
            for i, d in enumerate(days):
                row = build_dev_row(
                    asof=d,
                    instrument="KOSPI",
                    model_family="KOSPI_INDEX",
                    days=days,
                    i=i,
                    closes=kospi_closes,
                    bench_closes=kospi_closes,
                    bench_days=days,
                    cfg=cfg,
                )
                if row:
                    rows.append(row)
            instruments_rows["KOSPI"] = rows
        else:
            days = sorted(set(eval_days) & set(closes.keys()))
            rows = []
            for i, d in enumerate(days):
                row = build_dev_row(
                    asof=d,
                    instrument=spec["id"],
                    model_family="SINGLE_NAME",
                    days=days,
                    i=i,
                    closes=closes,
                    bench_closes=kospi_closes,
                    bench_days=sorted(kospi_closes.keys()),
                    cfg=cfg,
                )
                if row:
                    rows.append(row)
            instruments_rows[spec["id"]] = rows
        entry["status"] = "INCLUDED"
        entry["n_rows"] = len(instruments_rows[spec["id"]])
        entry["n_days_window"] = len(eval_days)
        panel_status.append(entry)

    included = [e["id"] for e in panel_status if e.get("status") == "INCLUDED"]
    if included != EXPECTED_UNIVERSE:
        return {
            "ok": False,
            "error": "UNIVERSE_NOT_EXACT",
            "got": included,
            "expected": EXPECTED_UNIVERSE,
            "prereg": prereg,
            "freeze_verify": freeze_verify,
            "nonoverlap_proof": proof,
        }

    leak_events: list[dict[str, Any]] = []
    for inst, rows in instruments_rows.items():
        for r in rows:
            for flag in r.leakage_flags:
                leak_events.append({"instrument": inst, "asof": r.asof, "flag": flag})
            for axis, ts in r.feature_timestamps.items():
                if ts not in ("UNKNOWN", "N_A_FOR_INDEX") and str(ts)[:10] > r.asof:
                    leak_events.append(
                        {
                            "instrument": inst,
                            "asof": r.asof,
                            "flag": "timestamp_post_asof",
                            "axis": axis,
                            "ts": ts,
                        }
                    )
    hard_fail = sum(1 for e in leak_events if e.get("flag") == "timestamp_post_asof")
    leakage_audit = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_leakage_audit_v1",
        "generated_at_utc": _utc(),
        "label": window_meta.get("window_label"),
        "research_only": True,
        "point_in_time_wall": True,
        "n_events": len(leak_events),
        "events_sample": leak_events[:30],
        "hard_fail_post_asof_count": hard_fail,
        "pass_if_hard_fail_zero": True,
        "includes_3_lens": False,
        "realized_return_label_only": True,
    }

    pred_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    metric_cells: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    no_call_stats: dict[str, Any] = {}
    wf_meta: dict[str, Any] = {"by_instrument": {}}
    kospi_by_date = {r.asof: r for r in instruments_rows.get("KOSPI", [])}

    for inst_id, frows in instruments_rows.items():
        by_date = {r.asof: r for r in frows}
        days = [r.asof for r in frows]
        n = len(days)
        folds = build_walk_forward_folds(n, cfg)
        wf_meta["by_instrument"][inst_id] = {
            "n_days": n,
            "n_folds": len(folds),
            "wf_mode": (
                "frozen_expanding_purged_embargo" if folds else "frozen_wf_infeasible_zero_folds"
            ),
            "walk_forward_frozen": cfg.get("walk_forward"),
        }
        no_call_stats[inst_id] = {"NO_CALL": 0, "directional": 0, "by_reason": {}}
        fam = cfg["model_families"][frows[0].model_family if frows else "SINGLE_NAME"]
        up_cut = float(fam["score_to_action"]["up_cut"])
        down_cut = float(fam["score_to_action"]["down_cut"])
        for h in HORIZONS:
            for fold in folds:
                train_days = days[fold["train_start"] : fold["train_end"]]
                test_days = days[fold["test_start"] : fold["test_end"]]
                train_labs = []
                for td in train_days:
                    lab = (by_date[td].labels.get(h) or {}).get("y_sign")
                    if lab in CLASSES:
                        train_labs.append(lab)
                maj = _majority(train_labs) if train_labs else "FLAT"
                for td in test_days:
                    fr = by_date[td]
                    lab = (fr.labels.get(h) or {}).get("y_sign")
                    if lab not in CLASSES:
                        continue
                    action = fr.call_or_NO_CALL
                    if action == "NO_CALL":
                        no_call_stats[inst_id]["NO_CALL"] += 1
                        reason = fr.no_call_reason or "unspecified"
                        no_call_stats[inst_id]["by_reason"][reason] = (
                            no_call_stats[inst_id]["by_reason"].get(reason, 0) + 1
                        )
                    else:
                        no_call_stats[inst_id]["directional"] += 1
                    try:
                        di = days.index(td)
                    except ValueError:
                        di = -1
                    prev_sign = "FLAT"
                    if di >= 1:
                        prev = (by_date[days[di - 1]].labels.get(h) or {}).get("y_sign")
                        if prev in CLASSES:
                            prev_sign = prev
                    if fr.score is None or abs(fr.score) < 1e-12:
                        simple_mom = "FLAT"
                    else:
                        simple_mom = "UP" if fr.score > 0 else "DOWN"
                    price_only = _price_only_action(
                        float(fr.score) * 0.03 if fr.score is not None else None,
                        up_cut,
                        down_cut,
                    )
                    mkt = kospi_by_date.get(td)
                    market_only = (
                        mkt.call_or_NO_CALL
                        if mkt and mkt.call_or_NO_CALL in CLASSES + ("NO_CALL",)
                        else "FLAT"
                    )
                    if market_only == "NO_CALL":
                        market_only = "FLAT"
                    y_res = (fr.labels.get(h) or {}).get("y_residual")
                    row_out = {
                        "asof_date": td,
                        "instrument": inst_id,
                        "model_family": fr.model_family,
                        "horizon": h,
                        "fold": fold["fold"],
                        "target_id": (fr.labels.get(h) or {}).get("target_id"),
                        "y_residual": y_res,
                        "y_sign": lab,
                        "score": fr.score,
                        "confidence": fr.confidence,
                        "call_or_NO_CALL": action,
                        "pred_field": action if action in CLASSES + ("NO_CALL",) else "NO_CALL",
                        "no_call_reason": fr.no_call_reason,
                        "baseline_majority_class": maj,
                        "baseline_always_up": "UP",
                        "baseline_always_neutral": "FLAT",
                        "baseline_previous_direction": prev_sign,
                        "baseline_simple_momentum": simple_mom,
                        "baseline_market_only": market_only,
                        "baseline_price_only": price_only,
                        "lane": "research_only",
                        "label": window_meta.get("window_label"),
                        "research_only": True,
                    }
                    pred_rows.append(row_out)
                    label_rows.append(
                        {
                            "asof_date": td,
                            "instrument": inst_id,
                            "horizon": h,
                            "y_sign": lab,
                            "y_residual": y_res,
                            "realized_return_is_label_only": True,
                        }
                    )
                    metric_cells[(inst_id, h)].append(row_out)

    for inst_id in EXPECTED_UNIVERSE:
        for h in HORIZONS:
            metric_cells.setdefault((inst_id, h), [])

    qual_table: list[dict[str, Any]] = []
    stats_by_cell: dict[str, Any] = {}
    baseline_comparison: dict[str, Any] = {}
    null_ci_by_cell: dict[str, Any] = {}
    no_call_by_cell: dict[str, Any] = {}

    for (inst, h), rows in sorted(metric_cells.items()):
        field_m = compute_metrics(rows, pred_key="pred_field", label_key="y_sign", ret_key="y_residual")
        base_blocks: dict[str, Any] = {}
        for bname, bkey in (
            ("majority_class", "baseline_majority_class"),
            ("always_up", "baseline_always_up"),
            ("always_neutral", "baseline_always_neutral"),
            ("previous_direction", "baseline_previous_direction"),
            ("simple_momentum", "baseline_simple_momentum"),
            ("market_only", "baseline_market_only"),
            ("price_only", "baseline_price_only"),
        ):
            brows = [
                {
                    "pred_field": r.get(bkey) if r.get(bkey) in CLASSES else "FLAT",
                    "y_sign": r.get("y_sign"),
                    "y_residual": r.get("y_residual"),
                    "score": 0.0,
                }
                for r in rows
            ]
            bm = compute_metrics(brows, pred_key="pred_field", label_key="y_sign", ret_key="y_residual")
            base_blocks[bname] = {
                "MCC_called_only": bm.get("MCC_called_only"),
                "balanced_accuracy_called_only": bm.get("balanced_accuracy_called_only"),
                "directional_accuracy_called_only": bm.get("directional_accuracy_called_only"),
                "n_called": bm.get("n_called"),
            }
        best_name = None
        best_mcc: float | None = None
        for bname, block in base_blocks.items():
            mcc_b = block.get("MCC_called_only")
            if mcc_b is None:
                continue
            if best_mcc is None or float(mcc_b) > best_mcc:
                best_mcc = float(mcc_b)
                best_name = bname
        fmcc = field_m.get("MCC_called_only")
        delta_best = (
            (float(fmcc) - float(best_mcc)) if fmcc is not None and best_mcc is not None else None
        )
        seed_cell = SEED + abs(hash((inst, h))) % 10000
        boot = _bootstrap_mcc_ci(rows, n_boot=BOOT_N, seed=seed_cell)
        perm = _permutation_mcc_null(rows, n_perm=200, seed=seed_cell)
        eqcov = _equal_coverage_always_up(rows, seed=seed_cell + 99)
        per_class = _per_class_pr(rows)
        deltas_pack = {
            "best_naive_baseline": best_name,
            "best_naive_MCC": best_mcc,
            "delta_MCC_vs_best_naive": delta_best,
            "baselines": base_blocks,
        }
        if not rows:
            label, reasons = (
                "INSUFFICIENT_DATA",
                ["zero_oos_rows_frozen_wf_infeasible_or_empty_window"],
            )
        else:
            label, reasons = _qualify(
                field_m=field_m,
                deltas=deltas_pack,
                boot=boot,
                perm=perm,
                eqcov=eqcov,
                macro_low_entropy=macro_low_entropy,
            )
        cell_key = f"{inst}|{h}"
        qual_table.append(
            {
                "instrument": inst,
                "horizon": h,
                "qualification_label": label,
                "reasons": reasons,
                "MCC_called_only": field_m.get("MCC_called_only"),
                "BA_called_only": field_m.get("balanced_accuracy_called_only"),
                "dir_acc_called_only": field_m.get("directional_accuracy_called_only"),
                "per_class_precision_recall": per_class,
                "no_call_coverage": field_m.get("no_call_coverage"),
                "called_coverage": field_m.get("called_coverage"),
                "n_rows": field_m.get("n_rows") or len(rows),
                "n_called": field_m.get("n_called") or 0,
                "n_no_call": field_m.get("n_no_call") or 0,
                "delta_MCC_vs_best_naive": delta_best,
                "best_naive_baseline": best_name,
                "bootstrap_CI_excludes_zero": boot.get("excludes_zero"),
                "perm_p_exploratory": perm.get("p_two_sided"),
                "SIGNAL_CANDIDATE_NE_MARKET_ALPHA": True,
                "window_label": window_meta.get("window_label"),
                "multiple_comparison_exposure": True,
                "no_single_best_cell_cherry_pick": True,
            }
        )
        stats_by_cell[cell_key] = {
            "field_metrics": {
                k: field_m.get(k)
                for k in (
                    "MCC_called_only",
                    "balanced_accuracy_called_only",
                    "directional_accuracy_called_only",
                    "no_call_coverage",
                    "called_coverage",
                    "n_called",
                    "n_no_call",
                    "n_rows",
                )
            },
            "bootstrap_MCC_called_only": boot,
            "permutation_null_MCC": perm,
            "equal_coverage_always_up": eqcov,
            "per_class_precision_recall": per_class,
        }
        null_ci_by_cell[cell_key] = {
            "bootstrap_MCC_called_only": boot,
            "permutation_null_MCC": perm,
            "effect_size_delta_MCC_vs_best_naive": delta_best,
            "multiple_comparison_exposure": True,
        }
        no_call_by_cell[cell_key] = {
            "no_call_coverage": field_m.get("no_call_coverage"),
            "called_coverage": field_m.get("called_coverage"),
            "equal_coverage_always_up": eqcov,
            "full_metrics_n_rows": field_m.get("n_rows") or len(rows),
            "called_only_n": field_m.get("n_called") or 0,
        }
        baseline_comparison.setdefault(inst, {})[h] = {
            "model": {
                "MCC_called_only": field_m.get("MCC_called_only"),
                "balanced_accuracy_called_only": field_m.get("balanced_accuracy_called_only"),
                "directional_accuracy_called_only": field_m.get("directional_accuracy_called_only"),
            },
            "baselines": base_blocks,
            "delta_MCC_vs_best_naive": delta_best,
            "best_naive_baseline": best_name,
        }

    zero_folds_all = all(
        (wf_meta["by_instrument"].get(i) or {}).get("n_folds", 0) == 0 for i in EXPECTED_UNIVERSE
    )
    if zero_folds_all:
        for row in qual_table:
            if row["qualification_label"] == "SIGNAL_CANDIDATE":
                row["qualification_label"] = "INSUFFICIENT_DATA"
                row["reasons"] = ["failure_behavior_preserve_no_repair_demote_zero_folds"] + list(
                    row.get("reasons") or []
                )
            if not row.get("n_rows"):
                row["qualification_label"] = "INSUFFICIENT_DATA"
                row["reasons"] = ["zero_oos_rows_frozen_wf_infeasible_or_empty_window"]

    label_counts = Counter(r["qualification_label"] for r in qual_table)
    sc_count = int(label_counts.get("SIGNAL_CANDIDATE", 0))
    any_candidate = sc_count > 0

    qualification = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_qualification_v1",
        "generated_at_utc": _utc(),
        "label": window_meta.get("window_label"),
        "enum_same_as_phase3": True,
        "qualification_table": qual_table,
        "label_counts": dict(label_counts),
        "SIGNAL_CANDIDATE_count": sc_count,
        "any_SIGNAL_CANDIDATE": any_candidate,
        "SIGNAL_CANDIDATE_claimed": False,
        "SIGNAL_CANDIDATE_NE_MARKET_ALPHA": True,
        "MARKET_ALPHA_ESTABLISHED": False,
        "research_only": True,
        "send_gate": "HOLD",
        "live": False,
        "EVIDENCE_CEILING": EVIDENCE_CEILING,
    }

    summary = {
        "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "DECIDE_ONE": DECIDE_OK,
        "pass_ceiling": PASS_CEILING,
        "EVIDENCE_CEILING": EVIDENCE_CEILING,
        "CORE_RULE": CORE_RULE,
        "label": window_meta.get("window_label"),
        "window_meta": window_meta,
        "instruments": EXPECTED_UNIVERSE,
        "horizons": list(HORIZONS),
        "panel_status": panel_status,
        "n_pred_rows": len(pred_rows),
        "n_label_rows": len(label_rows),
        "leakage_hard_fail_count": hard_fail,
        "SIGNAL_CANDIDATE_count": sc_count,
        "any_SIGNAL_CANDIDATE": any_candidate,
        "SIGNAL_CANDIDATE_claimed": False,
        "MARKET_ALPHA_ESTABLISHED": False,
        "qualification_label_counts": dict(label_counts),
        "model_families_separate": True,
        "includes_3_lens": False,
        "tuning_after_results": False,
        "freeze_guard_held": True,
        "walk_forward_meta": wf_meta,
        "zero_frozen_wf_folds": zero_folds_all,
        "macro_bias_guard": {
            "low_macro_score_entropy": macro_low_entropy,
            "diagnostic_only_not_signal_alpha": True,
            "flags": macro_flags,
        },
        "research_only": True,
        "send_gate": "HOLD",
        "live": False,
        "auto_trade": False,
        "deploy": False,
        "track_a_ready": False,
        "product_done": False,
        "AUTO_NEXT": False,
        "on_pass": "STOP",
        "on_signal_candidate": "STOP",
        "on_no_signal": "STOP",
        "git_commit_sha": _git_sha(root),
        "SUCCESS_DOES_NOT_MEAN": [
            "MARKET_ALPHA_ESTABLISHED",
            "profitable_strategy",
            "future_generalization",
            "calibration_complete",
            "3_lens_validity",
            "PRODUCT_DONE",
            "SEND",
            "DEPLOY",
            "LIVE",
        ],
        "note_ko": "동결 Field V2 독립 비겹침 평가만. 개선/재튜닝 금지. SIGNAL_CANDIDATE=0이면 결과 보존·STOP.",
    }

    wf_need = 80 + 5 + 15
    n_bars = int(window_meta.get("n_bars") or 0)
    if zero_folds_all or len(pred_rows) == 0 or n_bars < wf_need:
        observed_result = "INSUFFICIENT_DATA"
        insufficient_reason = (
            window_meta.get("insufficient_reason")
            or "reserved_future_unseen_shorter_than_frozen_walk_forward"
        )
    elif sc_count == 0:
        observed_result = "ZERO_CANDIDATE"
        insufficient_reason = None
    else:
        observed_result = "PASS"
        insufficient_reason = None
    summary["observed_result"] = observed_result
    summary["ALLOWED_RESULT"] = ["PASS", "ZERO_CANDIDATE", "INSUFFICIENT_DATA", "FAIL"]
    summary["insufficient_reason"] = insufficient_reason
    summary["pipeline_sealed"] = True
    summary["PASS_NE_PROFIT"] = True
    summary["PASS_NE_GENERALIZATION"] = True
    summary["PASS_NE_3_LENS_SUPERIORITY"] = True
    summary["PASS_NE_TRADE"] = True
    summary["ORACLE_SESSION_UPGRADE"] = "FAIL"
    summary["session_upgrade_not_reinterpreted_as_pass"] = True

    return {
        "ok": True,
        "prereg": prereg,
        "freeze_verify": freeze_verify,
        "nonoverlap_proof": proof,
        "prediction_rows": pred_rows,
        "label_rows": label_rows,
        "qualification": qualification,
        "baseline_comparison": {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_baseline_comparison_v1",
            "generated_at_utc": _utc(),
            "baselines": list(BASELINE_NAMES),
            "by_instrument": baseline_comparison,
            "SIGNAL_CANDIDATE_claimed": False,
            "MARKET_ALPHA_ESTABLISHED": False,
            "research_only": True,
        },
        "null_ci_report": {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_null_ci_v1",
            "generated_at_utc": _utc(),
            "bootstrap_n": BOOT_N,
            "permutation_n": 200,
            "seed": SEED,
            "by_cell": null_ci_by_cell,
            "multiple_comparison_exposure": True,
            "no_single_best_cell_cherry_pick": True,
            "research_only": True,
        },
        "no_call_report": {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_no_call_v1",
            "generated_at_utc": _utc(),
            "by_instrument": no_call_stats,
            "by_cell": no_call_by_cell,
            "report_full_and_called_only_and_equal_coverage": True,
            "research_only": True,
        },
        "leakage_audit": leakage_audit,
        "stats": {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_stats_v1",
            "generated_at_utc": _utc(),
            "by_cell": stats_by_cell,
            "research_only": True,
        },
        "summary": summary,
        "hashes": {
            "schema": "mkm_field_forecast_v2_independent_nonoverlap_eval_hashes_v1",
            "generated_at_utc": _utc(),
            "git_commit_sha": _git_sha(root),
            "refreeze_manifest_sha256": freeze_verify.get("refreeze_manifest_sha256"),
            "config_sha256": freeze_verify.get("config_sha256"),
            "prereg_window": {
                "date_start": window_meta.get("date_start"),
                "date_end": window_meta.get("date_end"),
                "label": window_meta.get("window_label"),
            },
            "research_only": True,
            "EVIDENCE_CEILING": EVIDENCE_CEILING,
        },
    }
