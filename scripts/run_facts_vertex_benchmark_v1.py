#!/usr/bin/env python3
"""FACTS-style benchmark: Vertex AI (GCP Billing/credits) + 단일 플래그십 모델.

파이프라인:
  answer-key JSONL → 모델 호출(행별) → predictions JSONL → ``run_facts_minimal_eval_v1.py`` 채점
  → 통합 리포트 ``facts_vertex_benchmark_latest.json``

인증: ADC(gcloud adc 또는 GOOGLE_APPLICATION_CREDENTIALS) + GOOGLE_CLOUD_PROJECT + 리전.
기본 모델(단일 최고): ``gemini-2.5-pro`` — 리전/프로젝트에서 미개시 시 ``--model`` 로 조정.

Answer-key 행 권장 필드: ``id``, ``question``, ``answer``, 선택 ``is_unknown``.
``question`` 이 없으면 ``--allow-missing-question`` 또는 ``--dry-run`` 필요.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Vertex 단일 플래그십(프로젝트·리전별 사용 가능 모델은 콘솔/SDK와 대조)
DEFAULT_VERTEX_FLAGSHIP_MODEL = "gemini-2.5-pro"

QUESTION_ALIASES = ["question", "prompt", "query", "text", "q"]
ID_ALIASES = ["id", "qid", "question_id", "example_id"]
ANSWER_ALIASES = ["answer", "gold_answer", "reference_answer", "target"]
UNKNOWN_ALIASES = ["is_unknown", "unanswerable", "unknown"]


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError(f"Row must be object at {path}:{line_no}")
            rows.append(obj)
    return rows


def _pick_field(row: dict[str, Any], aliases: list[str]) -> Any:
    for k in aliases:
        if k in row:
            return row.get(k)
    return None


def _vertex_project() -> str | None:
    for key in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_PROJECT_ID", "GOOGLE_GENAI_PROJECT"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return None


def _vertex_location() -> str:
    return (
        (os.environ.get("GOOGLE_CLOUD_LOCATION") or "").strip()
        or (os.environ.get("GOOGLE_GENAI_LOCATION") or "").strip()
        or "us-central1"
    )


def _balanced_brace_object(s: str, start: int) -> str | None:
    """Return substring from first `{` at/after start through matching `}` (string-aware)."""
    i = s.find("{", start)
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(s)):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i : j + 1]
    return None


def _regex_extract_decision_prediction(s: str) -> dict[str, Any] | None:
    """Last-resort parse when JSON is truncated or has stray characters."""
    dm = re.search(r'"decision"\s*:\s*"([^"]*)"', s, re.I)
    if not dm:
        dm = re.search(r'"decision"\s*:\s*([A-Za-z]+)', s)
    if not dm:
        return None
    dec = dm.group(1).strip().upper()
    pred = ""
    if re.search(r'"prediction"\s*:\s*""', s):
        pred = ""
    else:
        pm = re.search(r'"prediction"\s*:\s*"((?:[^"\\]|\\.)*)"', s)
        if pm:
            pred = pm.group(1)
        else:
            pm2 = re.search(r'"prediction"\s*:\s*"([^"]*)', s)
            if pm2:
                pred = pm2.group(1)
    return {"decision": dec, "prediction": pred}


def _extract_json_object(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if not s:
        raise ValueError("empty model response")
    # fenced blocks: take first JSON-looking slice inside ``` blocks
    if "```" in s:
        parts = re.split(r"```(?:json)?", s, flags=re.IGNORECASE)
        for chunk in parts:
            chunk = chunk.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].lstrip()
            blob = _balanced_brace_object(chunk, 0)
            if blob:
                try:
                    obj = json.loads(blob)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    fb = _regex_extract_decision_prediction(blob)
                    if fb:
                        return fb
                    continue
    blob = _balanced_brace_object(s, 0)
    if blob:
        try:
            obj = json.loads(blob)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            fb = _regex_extract_decision_prediction(blob)
            if fb:
                return fb
    fb = _regex_extract_decision_prediction(s)
    if fb:
        return fb
    raise ValueError(f"Could not parse JSON object from: {s[:240]}…")


def _normalize_decision(raw: Any) -> str:
    if raw is None:
        return "HOLD"
    u = str(raw).strip().upper()
    if u in {"HOLD", "ABSTAIN", "DEFER", "UNSURE"}:
        return "HOLD"
    if u in {"ANSWER", "A", "YES"}:
        return "ANSWER"
    return "ANSWER" if u else "HOLD"


def _build_prompt(question: str) -> str:
    return (
        "You are a factual QA benchmark participant. Output exactly one JSON object with keys:\n"
        '  "decision": "ANSWER" or "HOLD"\n'
        '  "prediction": short factual string (empty string if HOLD)\n'
        "\n"
        "Rules:\n"
        "- Use HOLD when the question is unanswerable or you are uncertain.\n"
        "- Keep prediction minimal (short phrase or single token when possible).\n"
        "\n"
        f"Question:\n{question}\n"
        "\n"
        "JSON object only."
    )


def _run_eval_subprocess(
    *,
    answer_key: Path,
    predictions: Path,
    out_eval: Path,
    preset: str,
    unknown_field: str | None,
) -> None:
    cmd = [
        sys.executable,
        str(_REPO_ROOT / "scripts" / "run_facts_minimal_eval_v1.py"),
        "--preset",
        preset,
        "--answer-key-jsonl",
        str(answer_key),
        "--predictions-jsonl",
        str(predictions),
        "--out-json",
        str(out_eval),
    ]
    if unknown_field:
        cmd.extend(["--unknown-field", unknown_field])
    proc = subprocess.run(cmd, cwd=str(_REPO_ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise RuntimeError(f"run_facts_minimal_eval_v1.py exit {proc.returncode}")


def main() -> int:
    ap = argparse.ArgumentParser(description="FACTS Vertex benchmark (single flagship model)")
    ap.add_argument("--answer-key-jsonl", type=Path, required=True)
    ap.add_argument(
        "--model",
        default=DEFAULT_VERTEX_FLAGSHIP_MODEL,
        help=f"Vertex model id (default: {DEFAULT_VERTEX_FLAGSHIP_MODEL})",
    )
    ap.add_argument(
        "--out-predictions-jsonl",
        type=Path,
        default=_REPO_ROOT / "docs/final/artifacts/facts_vertex_predictions_latest.jsonl",
    )
    ap.add_argument(
        "--out-eval-json",
        type=Path,
        default=_REPO_ROOT / "docs/final/artifacts/facts_minimal_eval_latest.json",
    )
    ap.add_argument(
        "--out-report-json",
        type=Path,
        default=_REPO_ROOT / "docs/final/artifacts/facts_vertex_benchmark_latest.json",
    )
    ap.add_argument("--preset", default="google_facts", help="Eval preset for run_facts_minimal_eval_v1")
    ap.add_argument(
        "--unknown-field",
        default=None,
        help="Optional; forwarded to eval if set (else eval resolves from preset)",
    )
    ap.add_argument("--limit", type=int, default=0, help="Only first N rows (0=all)")
    ap.add_argument("--sleep-ms", type=int, default=0, help="Pause between API calls")
    ap.add_argument(
        "--allow-missing-question",
        action="store_true",
        help="Use placeholder text when question field is missing",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="No Vertex calls; predictions copied from gold (offline pipeline check)",
    )
    args = ap.parse_args()

    if not args.answer_key_jsonl.is_file():
        print(f"[ERROR] missing answer key: {args.answer_key_jsonl}", file=sys.stderr)
        return 2

    rows_full = _read_jsonl(args.answer_key_jsonl)
    rows = rows_full
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    answer_key_for_eval = args.answer_key_jsonl
    if len(rows) < len(rows_full):
        slice_path = (
            args.out_predictions_jsonl.parent
            / f"{args.answer_key_jsonl.stem}_slice_{len(rows)}.jsonl"
        )
        slice_path.parent.mkdir(parents=True, exist_ok=True)
        with slice_path.open("w", encoding="utf-8") as sf:
            for r in rows:
                sf.write(json.dumps(r, ensure_ascii=False) + "\n")
        answer_key_for_eval = slice_path

    id_key = None
    for cand in ID_ALIASES:
        if rows and cand in rows[0]:
            id_key = cand
            break
    if not id_key:
        raise ValueError(f"Could not resolve id field from aliases {ID_ALIASES}")

    preds_out: list[dict[str, str]] = []
    timings_ms: list[float] = []
    project: str | None = None

    if args.dry_run:
        project = _vertex_project()
        for row in rows:
            rid = str(row[id_key])
            gold = _pick_field(row, ANSWER_ALIASES)
            unk_val = _pick_field(row, UNKNOWN_ALIASES)
            is_u = str(unk_val).strip().lower() in {"true", "1", "yes", "unknown", "unanswerable"}
            if is_u:
                preds_out.append({"id": rid, "decision": "HOLD", "prediction": ""})
            else:
                preds_out.append(
                    {"id": rid, "decision": "ANSWER", "prediction": "" if gold is None else str(gold)}
                )
        billing_surface = "dry_run"
    else:
        proj = _vertex_project()
        if not proj:
            print(
                "[ERROR] Vertex: set GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_PROJECT_ID",
                file=sys.stderr,
            )
            return 2
        location = _vertex_location()
        project = proj
        billing_surface = "vertex_ai"

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            print("pip install google-genai", file=sys.stderr)
            return 2

        client = genai.Client(vertexai=True, project=proj, location=location)

        for row in rows:
            rid = str(row[id_key])
            q = _pick_field(row, QUESTION_ALIASES)
            if q is None or not str(q).strip():
                if args.allow_missing_question:
                    q = f"(benchmark item {rid}; no question text provided)"
                else:
                    raise ValueError(
                        f"Row {rid}: missing question field; add question/prompt or --allow-missing-question"
                    )

            prompt = _build_prompt(str(q).strip())
            t0 = time.perf_counter()
            resp = client.models.generate_content(
                model=args.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.1,
                ),
            )
            timings_ms.append((time.perf_counter() - t0) * 1000.0)
            raw_text = (resp.text or "").strip()
            try:
                obj = _extract_json_object(raw_text)
            except Exception as exc:
                print(f"[WARN] id={rid} parse failed ({exc}); defaulting HOLD", file=sys.stderr)
                preds_out.append({"id": rid, "decision": "HOLD", "prediction": ""})
                continue

            dec = _normalize_decision(obj.get("decision"))
            pred = obj.get("prediction")
            pred_s = "" if pred is None else str(pred).strip()
            if dec == "HOLD":
                pred_s = ""
            preds_out.append({"id": rid, "decision": dec, "prediction": pred_s})

            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)

    args.out_predictions_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_predictions_jsonl.open("w", encoding="utf-8") as f:
        for p in preds_out:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    ak_sha = _sha256_file(answer_key_for_eval)
    pred_sha = _sha256_file(args.out_predictions_jsonl)

    args.out_eval_json.parent.mkdir(parents=True, exist_ok=True)
    unknown_fwd = args.unknown_field
    _run_eval_subprocess(
        answer_key=answer_key_for_eval,
        predictions=args.out_predictions_jsonl,
        out_eval=args.out_eval_json,
        preset=args.preset,
        unknown_field=unknown_fwd,
    )

    eval_body = json.loads(args.out_eval_json.read_text(encoding="utf-8"))

    report = {
        "schema": "facts_vertex_benchmark_v1",
        "generated_at_utc": _now_utc_iso(),
        "billing_surface": billing_surface,
        "vertex_project": project,
        "vertex_location": _vertex_location(),
        "model": args.model if not args.dry_run else "dry_run",
        "dry_run": args.dry_run,
        "answer_key_jsonl": str(args.answer_key_jsonl),
        "answer_key_used_for_eval_jsonl": str(answer_key_for_eval),
        "answer_key_sha256": ak_sha,
        "predictions_jsonl": str(args.out_predictions_jsonl),
        "predictions_sha256": pred_sha,
        "eval_json": str(args.out_eval_json),
        "eval": eval_body,
    }
    if timings_ms:
        report["timing_ms"] = {
            "rows": len(timings_ms),
            "mean": sum(timings_ms) / len(timings_ms),
            "max": max(timings_ms),
        }

    args.out_report_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] predictions: {args.out_predictions_jsonl}")
    print(f"[OK] eval:       {args.out_eval_json}")
    print(f"[OK] report:     {args.out_report_json}")
    m = eval_body.get("metrics", {})
    print(
        "[SUMMARY] "
        f"coverage={m.get('coverage')}, answered_acc={m.get('answered_accuracy')}, "
        f"hold_rate={m.get('hold_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
