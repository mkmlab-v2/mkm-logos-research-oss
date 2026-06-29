#!/usr/bin/env python3
"""PROMPT_DRYRUN_LOCAL — Ollama 8B-class + birth_anchor few-shot MKM lens alignment [HYPO].

B-track only: no Track A / live trading / Nemotron LoRA wire.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/prompt_dryrun_local_mkm_lens_v1_latest.json"
BASE_SYSTEM = ROOT / "reports/ollama_gemma_local_system_prompt_v1.txt"
DEFAULT_MODEL = "llama3.1:8b"
FALLBACK_MODEL = "gemma4:e2b"
DEMO_UTC = "1992-03-12T17:00:00Z"
DEMO_TZ = "Asia/Seoul"

USER_PROMPT = """birth_anchor JSON만 ground truth. 사주 수치를 추측·변경 금지.

각 1~2문장. 아래 태그 문자열을 그대로 출력:
1) 명리: engine_inputs(년월일시)만 인용.
2) 사상: 반드시 `[HYPO]` 포함.
3) 성경(Logos): 반드시 `[NON_GATING]` 포함 — 가격·매매 지시 금지.

마지막 줄 필수(한 줄): Final Action = HOLD 또는 WATCH"""

SWEEP_PROFILES: tuple[dict[str, object], ...] = (
    {"label": "seoul_1992", "utc_instant": "1992-03-12T17:00:00Z", "iana_tz": "Asia/Seoul"},
    {"label": "seoul_1971", "utc_instant": "1971-05-20T08:13:00Z", "iana_tz": "Asia/Seoul"},
    {"label": "nyc_1990", "utc_instant": "1990-07-04T16:00:00Z", "iana_tz": "America/New_York"},
    {
        "label": "ladakh_2021",
        "local": [2021, 1, 5, 19, 0, 0],
        "iana_tz": "Asia/Kolkata",
        "place": "ladakh",
    },
)
SWEEP_OUT = ROOT / "reports/prompt_dryrun_local_mkm_lens_sweep_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_birth_local(local: list[int], iana_tz: str) -> dict:
    if len(local) != 6:
        raise ValueError("local must be [Y,M,D,h,m,s]")
    y, m, d, h, mi, s = local
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_saju_global_birth_v1.py"),
            "--local",
            str(y),
            str(m),
            str(d),
            str(h),
            str(mi),
            str(s),
            "--iana-tz",
            iana_tz,
            "--compact",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "birth resolve failed")[:500])
    return json.loads(cp.stdout.strip())


def _resolve_profile(prof: dict[str, object]) -> dict:
    if "local" in prof:
        local = prof["local"]
        if not isinstance(local, list):
            raise ValueError("local profile must be a list")
        return _resolve_birth_local([int(x) for x in local], str(prof["iana_tz"]))
    return _resolve_birth(str(prof["utc_instant"]), str(prof["iana_tz"]))


def _resolve_birth(utc_instant: str, iana_tz: str) -> dict:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_saju_global_birth_v1.py"),
            "--utc-instant",
            utc_instant,
            "--iana-tz",
            iana_tz,
            "--compact",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if cp.returncode != 0:
        raise RuntimeError((cp.stderr or cp.stdout or "birth resolve failed")[:500])
    return json.loads(cp.stdout.strip())


def _compact_anchor(doc: dict) -> dict:
    res = doc.get("resolution") or {}
    full = doc.get("full_saju") or {}
    saju = full.get("saju") if isinstance(full.get("saju"), dict) else {}
    return {
        "schema": "birth_anchor_v1",
        "birth_instant_utc": (res.get("birth_instant_utc") or ""),
        "iana_tz": res.get("iana_tz") or "",
        "engine_inputs": (res.get("engine_inputs") or {}),
        "saju_code": saju.get("code") or full.get("birth_info", {}).get("saju_code"),
        "warnings": res.get("warnings") or [],
    }


def _build_system(base_file: Path, anchor: dict) -> str:
    local_date = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
    base = ""
    if base_file.is_file():
        base = base_file.read_text(encoding="utf-8").replace("{{DATE}}", local_date).strip()
    mkm = """
MKM lens contract (research_only · B-track):
- Render: Field → Lens(사상/명리/성경) → Conflict → Final Action(HOLD/WATCH/REDUCE).
- 명리 = deterministic birth profile anchor only; do not replace with market day pillars.
- 사상 = short-horizon intensity overlay — always tag [HYPO].
- 성경(Logos) = [NON_GATING] narrative guard only — never price triggers.
- Never claim live trading, Track A promotion, or web search.
""".strip()
    anchor_block = json.dumps(anchor, ensure_ascii=False, indent=2)
    return f"{base}\n\n{mkm}\n\nbirth_anchor JSON (FACT for this turn):\n{anchor_block}"


def _pick_model(requested: str) -> str:
    return requested or DEFAULT_MODEL


def _run_ollama(model: str, system: str, prompt: str, out_json: Path) -> dict:
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/ollama_local_smoke_v1.py"),
            "--model",
            model,
            "--system",
            system[:12000],
            "--prompt",
            prompt,
            "--timeout-sec",
            "240",
            "--out-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    doc: dict = {"exit_code": cp.returncode}
    if out_json.is_file():
        doc.update(json.loads(out_json.read_text(encoding="utf-8")))
    if cp.returncode != 0 and "error" not in doc:
        doc["error"] = (cp.stderr or "")[-400:]
    return doc


def _score(response: str, anchor: dict) -> dict:
    text = response or ""
    eng = anchor.get("engine_inputs") or {}
    year_str = str(eng.get("year") or "")
    forbidden_trade = bool(re.search(r"매수|매도|실매매|live trading|Track A 승격", text, re.I))
    has_hypo = "[HYPO]" in text or "가설" in text
    has_non_gating = "[NON_GATING]" in text or "NON_GATING" in text.upper()
    mentions_engine = year_str != "" and year_str in text
    has_hold_watch = bool(re.search(r"\b(HOLD|WATCH|REDUCE)\b", text, re.I))
    claims_search = bool(re.search(r"검색했|구글|browse|web search", text, re.I))
    return {
        "forbidden_trade_language": forbidden_trade,
        "has_hypo_tag_or_ko": has_hypo,
        "has_non_gating": has_non_gating,
        "mentions_birth_engine_year": mentions_engine,
        "has_final_action_token": has_hold_watch,
        "claims_web_search": claims_search,
        "pass_heuristic": (
            not forbidden_trade
            and not claims_search
            and has_hypo
            and has_non_gating
            and mentions_engine
            and has_hold_watch
        ),
    }


def run_profile(prof: dict[str, object], model: str, system_file: Path) -> dict:
    birth_doc = _resolve_profile(prof)
    anchor = _compact_anchor(birth_doc)
    system = _build_system(system_file, anchor)
    user_prompt = USER_PROMPT + "\n\nbirth_anchor:\n" + json.dumps(anchor, ensure_ascii=False)

    picked = _pick_model(model)
    smoke_out = ROOT / "reports/prompt_dryrun_local_mkm_lens_ollama_smoke_latest.json"
    ollama = _run_ollama(picked, system, user_prompt, smoke_out)
    if not ollama.get("ok") and picked == DEFAULT_MODEL:
        picked = FALLBACK_MODEL
        ollama = _run_ollama(picked, system, user_prompt, smoke_out)

    response = str(ollama.get("response_preview") or "")
    score = _score(response, anchor)
    row: dict[str, object] = {
        "label": str(prof.get("label") or ""),
        "iana_tz": str(prof.get("iana_tz") or ""),
        "birth_anchor": anchor,
        "model": picked,
        "ollama_ok": bool(ollama.get("ok")),
        "response_preview": response[:1200],
        "score": score,
    }
    if "utc_instant" in prof:
        row["utc_instant"] = prof["utc_instant"]
    if "local" in prof:
        row["local"] = prof["local"]
        row["place"] = prof.get("place")
    return row


def run_single(
    *,
    utc_instant: str,
    iana_tz: str,
    model: str,
    system_file: Path,
    label: str = "",
) -> dict:
    prof: dict[str, object] = {
        "label": label or f"{iana_tz}:{utc_instant}",
        "utc_instant": utc_instant,
        "iana_tz": iana_tz,
    }
    return run_profile(prof, model, system_file)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--utc-instant", default=DEMO_UTC)
    ap.add_argument("--iana-tz", default=DEMO_TZ)
    ap.add_argument("--model", default="", help=f"default {DEFAULT_MODEL}, fallback {FALLBACK_MODEL}")
    ap.add_argument("--system-file", type=Path, default=BASE_SYSTEM)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sweep-defaults", action="store_true", help="Run 4-profile birth_anchor alignment sweep")
    ap.add_argument("--strict", action="store_true", help="exit 1 unless pass_heuristic")
    args = ap.parse_args()

    if args.sweep_defaults:
        rows: list[dict] = []
        for prof in SWEEP_PROFILES:
            try:
                row = run_profile(prof, args.model, args.system_file)
            except Exception as e:
                row = {
                    "label": prof.get("label"),
                    "iana_tz": prof.get("iana_tz"),
                    "ollama_ok": False,
                    "error": str(e)[:400],
                    "score": {"pass_heuristic": False},
                }
                if "utc_instant" in prof:
                    row["utc_instant"] = prof["utc_instant"]
                if "local" in prof:
                    row["local"] = prof["local"]
                    row["place"] = prof.get("place")
            rows.append(row)

        n_pass = sum(1 for r in rows if (r.get("score") or {}).get("pass_heuristic"))
        sweep_doc = {
            "schema": "prompt_dryrun_local_mkm_lens_sweep_v1",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "auto_apply": False,
            "track_wall": "no_track_a_live_auto_merge",
            "action_id": "PROMPT_DRYRUN_LOCAL_SWEEP",
            "profiles": list(SWEEP_PROFILES),
            "rows": rows,
            "n_profiles": len(rows),
            "n_pass_heuristic": n_pass,
            "all_pass": n_pass == len(rows) and all(r.get("ollama_ok") for r in rows),
            "verdict_ko": (
                f"4-profile few-shot 정합 {n_pass}/{len(rows)} pass — "
                "LoRA/Track A/실매매 합선 없음 [HYPO]"
            ),
        }
        SWEEP_OUT.parent.mkdir(parents=True, exist_ok=True)
        SWEEP_OUT.write_text(json.dumps(sweep_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        args.out_json.write_text(
            json.dumps(
                {
                    **sweep_doc,
                    "schema": "prompt_dryrun_local_mkm_lens_v1",
                    "action_id": "PROMPT_DRYRUN_LOCAL",
                    "note": "latest single pointer; see sweep file for all rows",
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "ok": all(r.get("ollama_ok") for r in rows),
                    "n_pass": n_pass,
                    "n_profiles": len(rows),
                    "out": str(SWEEP_OUT),
                },
                ensure_ascii=False,
            )
        )
        if not all(r.get("ollama_ok") for r in rows):
            return 2
        if args.strict and not sweep_doc["all_pass"]:
            return 1
        return 0

    row = run_single(
        utc_instant=args.utc_instant,
        iana_tz=args.iana_tz,
        model=args.model,
        system_file=args.system_file,
    )
    ollama_ok = row["ollama_ok"]
    score = row["score"]

    doc = {
        "schema": "prompt_dryrun_local_mkm_lens_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "action_id": "PROMPT_DRYRUN_LOCAL",
        "birth_anchor": row["birth_anchor"],
        "model": row["model"],
        "ollama": {"ok": ollama_ok},
        "response_preview": row["response_preview"],
        "score": score,
        "verdict_ko": (
            "Few-shot birth_anchor + MKM lens contract 정합 스모크 "
            + ("pass" if score["pass_heuristic"] else "partial/fail")
            + " — LoRA/Track A/실매매 합선 없음 [HYPO]"
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ollama_ok, "pass_heuristic": score["pass_heuristic"], "out": str(args.out_json)}, ensure_ascii=False))
    if not ollama_ok:
        return 2
    if args.strict and not score["pass_heuristic"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
