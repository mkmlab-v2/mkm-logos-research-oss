"""Shared golden views for Pack 0-B SFT and alignment eval (compact / pillars tiers)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def compact_expected_result(exp: dict[str, Any]) -> dict[str, Any]:
    """Drop bulky daewoon fields; keep deterministic pillars for v0 curriculum."""
    out = deepcopy(exp)
    fs = out.get("full_saju")
    if isinstance(fs, dict):
        fs = dict(fs)
        fs.pop("daewoon", None)
        fs.pop("daewoon_qiyun_v1", None)
        out["full_saju"] = fs
    return out


def pillars_view(exp: dict[str, Any]) -> dict[str, Any]:
    """Tier-1 alignment: four pillars + resolution engine_inputs only."""
    res = exp.get("resolution") if isinstance(exp.get("resolution"), dict) else {}
    ei = res.get("engine_inputs") if isinstance(res.get("engine_inputs"), dict) else {}
    fs = exp.get("full_saju") if isinstance(exp.get("full_saju"), dict) else {}
    saju = fs.get("saju") if isinstance(fs.get("saju"), dict) else {}
    ver = fs.get("verification") if isinstance(fs.get("verification"), dict) else {}
    return {
        "schema": exp.get("schema"),
        "version": exp.get("version"),
        "resolution": {
            "birth_instant_utc": res.get("birth_instant_utc"),
            "iana_tz": res.get("iana_tz"),
            "local_iso": res.get("local_iso"),
            "engine_inputs": dict(ei),
            "meta": res.get("meta"),
        },
        "full_saju": {
            "saju": dict(saju),
            "ilgan": fs.get("ilgan"),
            "verification": dict(ver) if ver else ver,
        },
    }


def _saju_pillars(res: dict[str, Any]) -> dict[str, str | None]:
    """Extract year/month/day/hour pillar strings (hour aliases time)."""
    fs = res.get("full_saju")
    if not isinstance(fs, dict):
        return {"year": None, "month": None, "day": None, "hour": None}
    saju = fs.get("saju")
    if not isinstance(saju, dict):
        return {"year": None, "month": None, "day": None, "hour": None}
    hour = saju.get("hour")
    if hour is None:
        hour = saju.get("time")
    return {
        "year": saju.get("year") if saju.get("year") is not None else None,
        "month": saju.get("month") if saju.get("month") is not None else None,
        "day": saju.get("day") if saju.get("day") is not None else None,
        "hour": hour if hour is not None else None,
    }


def _field_eq(a: Any, b: Any) -> bool:
    return a == b


def _scalar_field(name: str, expected: Any, predicted: Any) -> dict[str, Any]:
    return {
        "field": name,
        "match": _field_eq(expected, predicted),
        "expected": expected,
        "predicted": predicted,
    }


def build_field_diff_v1(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, Any]:
    """Field-level autopsy for Pack 0-B alignment (engine golden vs model JSON)."""
    exp_p = _saju_pillars(expected)
    pred_p = _saju_pillars(predicted)
    four_pillars: dict[str, Any] = {}
    pillar_hits = 0
    for key in ("year", "month", "day", "hour"):
        rec = _scalar_field(f"full_saju.saju.{key}", exp_p[key], pred_p[key])
        four_pillars[key] = rec
        if rec["match"]:
            pillar_hits += 1

    exp_res = expected.get("resolution") if isinstance(expected.get("resolution"), dict) else {}
    pred_res = predicted.get("resolution") if isinstance(predicted.get("resolution"), dict) else {}
    local_iso = _scalar_field("resolution.local_iso", exp_res.get("local_iso"), pred_res.get("local_iso"))

    exp_ei = exp_res.get("engine_inputs") if isinstance(exp_res.get("engine_inputs"), dict) else {}
    pred_ei = pred_res.get("engine_inputs") if isinstance(pred_res.get("engine_inputs"), dict) else {}
    ei_fields = {}
    ei_hits = 0
    for k in ("year", "month", "day", "hour"):
        rec = _scalar_field(f"resolution.engine_inputs.{k}", exp_ei.get(k), pred_ei.get(k))
        ei_fields[k] = rec
        if rec["match"]:
            ei_hits += 1

    exp_fs = expected.get("full_saju") if isinstance(expected.get("full_saju"), dict) else {}
    pred_fs = predicted.get("full_saju") if isinstance(predicted.get("full_saju"), dict) else {}
    ilgan = _scalar_field("full_saju.ilgan", exp_fs.get("ilgan"), pred_fs.get("ilgan"))

    exp_dw = exp_fs.get("daewoon")
    pred_dw = pred_fs.get("daewoon")
    exp_list = exp_dw if isinstance(exp_dw, list) else []
    pred_list = pred_dw if isinstance(pred_dw, list) else []
    per_cycle: list[dict[str, Any]] = []
    head_match = 0
    compare_n = min(len(exp_list), len(pred_list), 10)
    first_mismatch_index: int | None = None
    for i in range(compare_n):
        e_item = exp_list[i] if isinstance(exp_list[i], dict) else {}
        p_item = pred_list[i] if isinstance(pred_list[i], dict) else {}
        e_saju = e_item.get("saju")
        p_saju = p_item.get("saju")
        m = _field_eq(e_saju, p_saju)
        if m:
            head_match += 1
        elif first_mismatch_index is None:
            first_mismatch_index = i
        per_cycle.append(
            {
                "index": i,
                "match": m,
                "expected_saju": e_saju,
                "predicted_saju": p_saju,
            }
        )
    daewoon = {
        "expected_len": len(exp_list),
        "predicted_len": len(pred_list),
        "len_match": len(exp_list) == len(pred_list),
        "head_compare_n": compare_n,
        "head_saju_match_count": head_match,
        "head_saju_match_rate": round(head_match / compare_n, 6) if compare_n else None,
        "first_mismatch_index": first_mismatch_index,
        "per_cycle": per_cycle,
    }

    top_level = {
        "schema": _scalar_field("schema", expected.get("schema"), predicted.get("schema")),
        "version": _scalar_field("version", expected.get("version"), predicted.get("version")),
    }

    missing_paths: list[str] = []
    if not isinstance(predicted.get("full_saju"), dict):
        missing_paths.append("full_saju")
    elif not isinstance(pred_fs.get("saju"), dict):
        missing_paths.append("full_saju.saju")
    if not isinstance(predicted.get("resolution"), dict):
        missing_paths.append("resolution")

    return {
        "schema": "myeongri_deterministic_lora_field_diff_v1",
        "four_pillars": four_pillars,
        "four_pillars_match_count": pillar_hits,
        "four_pillars_match_rate": round(pillar_hits / 4, 6),
        "local_iso": local_iso,
        "engine_inputs": ei_fields,
        "engine_inputs_match_count": ei_hits,
        "engine_inputs_match_rate": round(ei_hits / 4, 6) if ei_fields else 0.0,
        "ilgan": ilgan,
        "daewoon": daewoon,
        "top_level": top_level,
        "missing_paths": missing_paths,
    }


def aggregate_field_diffs(per_row_diffs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize field diffs across rows (only rows that include field_diff)."""
    n = len(per_row_diffs)
    if n == 0:
        return {"rows": 0}

    def rate(key_path: str) -> float:
        hits = 0
        for d in per_row_diffs:
            fd = d.get("field_diff") or {}
            if key_path == "four_pillars":
                hits += 1 if fd.get("four_pillars_match_rate") == 1.0 else 0
            elif key_path == "local_iso":
                loc = fd.get("local_iso") or {}
                hits += 1 if loc.get("match") else 0
            elif key_path == "daewoon_len":
                dw = fd.get("daewoon") or {}
                hits += 1 if dw.get("len_match") else 0
        return round(hits / n, 6)

    pillar_key_rates: dict[str, float] = {}
    for pk in ("year", "month", "day", "hour"):
        hits = sum(
            1
            for d in per_row_diffs
            if ((d.get("field_diff") or {}).get("four_pillars") or {}).get(pk, {}).get("match")
        )
        pillar_key_rates[pk] = round(hits / n, 6)

    return {
        "rows": n,
        "four_pillars_all_match_rate": rate("four_pillars"),
        "four_pillars_by_key": pillar_key_rates,
        "local_iso_match_rate": rate("local_iso"),
        "daewoon_len_match_rate": rate("daewoon_len"),
        "ilgan_match_rate": round(
            sum(
                1
                for d in per_row_diffs
                if ((d.get("field_diff") or {}).get("ilgan") or {}).get("match")
            )
            / n,
            6,
        ),
    }


PILLARS_ONLY_SCHEMA = "myeongri_pillars_only_v1"


def pillars_only_supervision_v1(exp: dict[str, Any]) -> dict[str, Any]:
    """Tier-0 SFT target: four ganji pillars only (no daewoon, ilgan, resolution)."""
    p = _saju_pillars(exp)
    return {
        "schema": PILLARS_ONLY_SCHEMA,
        "version": "1.0.0",
        "saju": {
            "year": p["year"],
            "month": p["month"],
            "day": p["day"],
            "hour": p["hour"],
        },
    }


def four_pillars_from_parsed(parsed: dict[str, Any]) -> dict[str, str | None]:
    """Extract year/month/day/hour ganji from pillars-only or full birth-result JSON."""
    if parsed.get("schema") == PILLARS_ONLY_SCHEMA:
        saju = parsed.get("saju") if isinstance(parsed.get("saju"), dict) else {}
        hour = saju.get("hour")
        if hour is None:
            hour = saju.get("time")
        return {
            "year": saju.get("year"),
            "month": saju.get("month"),
            "day": saju.get("day"),
            "hour": hour,
        }
    return _saju_pillars(parsed)


def four_pillars_match(expected: dict[str, Any], parsed: dict[str, Any]) -> bool:
    exp_p = _saju_pillars(expected)
    pred_p = four_pillars_from_parsed(parsed)
    return all(exp_p[k] == pred_p[k] for k in ("year", "month", "day", "hour"))


def pred_shaped_for_field_diff(expected: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Shape tier-0 pillars-only JSON into pillars_view layout for field_diff autopsy."""
    if parsed.get("schema") == PILLARS_ONLY_SCHEMA:
        out = pillars_view(expected)
        fp = four_pillars_from_parsed(parsed)
        saju = out.setdefault("full_saju", {}).setdefault("saju", {})
        for k, v in fp.items():
            if v is not None:
                saju[k] = v
        return out
    return parsed


def instruction_pillars_only_from_golden_row(row: dict[str, Any]) -> str:
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    return (
        "Deterministic myeongri pillars task (Pack 0-B curriculum tier-0). "
        "Use ONLY the birth inputs below — do not invent or change birth_instant_utc, "
        "iana_tz, or is_male. Compute four ganji pillars from these inputs only.\n"
        f"Emit ONLY valid JSON for schema {PILLARS_ONLY_SCHEMA} with keys: "
        "schema, version, saju.year, saju.month, saju.day, saju.hour (ganji strings).\n"
        "Do NOT emit daewoon, ilgan, shensha, resolution, or saju_global_birth_result_v1.\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )


def instruction_from_golden_row(row: dict[str, Any], *, compact_output: bool = False) -> str:
    utc = str(row.get("birth_instant_utc") or "").strip()
    tz = str(row.get("iana_tz") or "").strip()
    male = row.get("is_male")
    male_s = "unspecified (engine default false)" if male is None else ("true" if male else "false")
    omit = (
        "omit daewoon/daewoon_qiyun_v1; include resolution, full_saju.saju, full_saju.ilgan, full_saju.verification"
        if compact_output
        else "fields: schema, version, resolution, full_saju; omit calculated_at under full_saju"
    )
    return (
        "Deterministic myeongri task (Pack 0-B). Use ONLY the birth inputs below — "
        "do not invent or change birth_instant_utc, iana_tz, or is_male. "
        "Compute four pillars (year/month/day/hour saju) from these inputs only.\n"
        f"Emit ONLY valid JSON for schema saju_global_birth_result_v1 ({omit}).\n"
        f"birth_instant_utc: {utc}\n"
        f"iana_tz: {tz}\n"
        f"is_male: {male_s}"
    )
