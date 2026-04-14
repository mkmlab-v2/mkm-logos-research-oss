# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.65, L:0.82, K:0.45, M:0.48}
# Balance: 82
# Purpose: Fill human.regime_id via Gemini (optional API) or offline heuristic from question/answer text.
# Keywords: b-track, human audit, gemini, heuristic, regime
"""Auto-fill human audit ``regime_id`` (LLM or heuristic).

NotebookLM MCP is not invocable from this batch script; use ``--provider gemini`` with
``GEMINI_API_KEY`` for cloud labels, or ``--provider heuristic`` for free rule-based labels.

Both are [HYPO] / not ground-truth human audit.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_WS = Path(__file__).resolve().parent.parent
_ART = _WS / "docs" / "final" / "artifacts"


def _load_workspace_dotenv() -> None:
    """Load ``C:\\workspace\\.env`` into os.environ if present; does not override existing keys."""
    path = _WS / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " #" in value:
            value = value.split(" #", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not key or key in os.environ:
            continue
        os.environ[key] = value
_DEFAULT_BUNDLE = _ART / "human_regime_audit_sample_latest.json"
_DEFAULT_OUT = _ART / "human_regime_audit_filled_llm_heuristic_v1.json"

_ALLOWED = frozenset({"imf", "lehman", "it_bubble", "covid", "normal", "unknown", "other"})

# First-match substring rules (aligned loosely with notebooklm mapping policy; B-track only).
_HEURISTIC_RULES: Sequence[Tuple[str, str]] = (
    ("pandemic", "covid"),
    ("covid", "covid"),
    ("lockdown", "covid"),
    ("imf", "imf"),
    ("dotcom", "it_bubble"),
    ("tech bubble", "it_bubble"),
    ("it bubble", "it_bubble"),
    ("asset bubble", "it_bubble"),
    ("speculative mania", "it_bubble"),
    ("irrational exuberance", "it_bubble"),
    ("lehman", "lehman"),
    ("subprime", "lehman"),
    ("credit crisis", "lehman"),
    ("financial crisis", "lehman"),
    ("recession", "lehman"),
    ("debt crisis", "imf"),
    ("currency crisis", "imf"),
    ("bubble", "it_bubble"),
    ("crisis", "lehman"),
    ("baseline", "normal"),
    ("steady", "normal"),
    ("range-bound", "normal"),
)


def _extract_json_blob(text: str) -> Any | None:
    text = (text or "").strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _heuristic_label(text: str) -> Tuple[str, float]:
    low = text.lower()
    for needle, rid in _HEURISTIC_RULES:
        if needle in low:
            return rid, 0.55
    return "unknown", 0.35


def _retryable_http(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, OSError, ConnectionError)):
        return True
    name = type(exc).__name__
    if "Timeout" in name or "timeout" in name.lower():
        return True
    try:
        import httpx  # type: ignore

        return isinstance(exc, (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.TimeoutException))
    except Exception:
        return False


def _batch_gemini(
    batch: Sequence[Mapping[str, Any]],
    *,
    model: str,
    timeout_sec: int,
) -> Dict[int, Tuple[str, float]]:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY required for --provider gemini")

    lines: List[str] = []
    for it in batch:
        aid = int(it.get("audit_id", -1))
        ctx = it.get("context") if isinstance(it.get("context"), Mapping) else {}
        q = str((ctx or {}).get("question") or "")
        a = str((ctx or {}).get("answer_excerpt") or "")
        lines.append(f"audit_id={aid}\nQUESTION: {q[:2000]}\nANSWER: {a[:3000]}")
    block = "\n---\n".join(lines)

    prompt = f"""You label financial-historical regime for B-track research only. Not trading advice.

For EACH block below, pick exactly one regime_id from:
imf, lehman, it_bubble, covid, normal, unknown, other

Return a single JSON object ONLY (no markdown):
{{"results":[{{"audit_id": <int>, "regime_id": "<enum>", "confidence": <float 0-1>}}, ...]}}

Blocks:
{block}
"""

    from google import genai
    from google.genai import types

    # google.genai HttpOptions.timeout is milliseconds; API minimum deadline is 10s.
    timeout_ms = max(10_000, int(timeout_sec) * 1000)
    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
    resp = client.models.generate_content(
        model=model,
        contents=[types.Part.from_text(text=prompt)],
        config=types.GenerateContentConfig(temperature=0.1),
    )
    raw = (resp.text or "").strip()
    doc = _extract_json_blob(raw)
    if not isinstance(doc, dict):
        raise RuntimeError(f"Gemini JSON parse failed. Raw (truncated): {raw[:1500]!r}")
    results = doc.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Expected results array in JSON")
    out: Dict[int, Tuple[str, float]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue
        try:
            aid = int(row.get("audit_id"))
        except (TypeError, ValueError):
            continue
        rid = str(row.get("regime_id") or "unknown").lower().strip()
        if rid not in _ALLOWED:
            rid = "unknown"
        try:
            conf = float(row.get("confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        conf = max(0.0, min(1.0, conf))
        out[aid] = (rid, conf)
    return out


def _gemini_resolve_batch(
    batch: List[Mapping[str, Any]],
    *,
    model: str,
    base_timeout: int,
    max_retries: int,
    backoff_sec: float,
    gemini_fallback_heuristic: bool,
) -> Dict[int, Tuple[str, float, str]]:
    """Retries, splits batch on persistent failure, single-item heuristic fallback."""
    if not batch:
        return {}

    last_err: Optional[BaseException] = None
    for attempt in range(max_retries):
        timeout_sec = base_timeout + attempt * 45
        try:
            part = _batch_gemini(batch, model=model, timeout_sec=timeout_sec)
            out: Dict[int, Tuple[str, float, str]] = {}
            for aid, (rid, conf) in part.items():
                out[aid] = (rid, conf, f"gemini:{model}")
            return out
        except Exception as e:  # noqa: BLE001
            last_err = e
            if _retryable_http(e) and attempt < max_retries - 1:
                time.sleep(backoff_sec * (2**attempt))
                continue
            break

    if len(batch) == 1:
        it = batch[0]
        try:
            aid = int(it.get("audit_id", -1))
        except (TypeError, ValueError):
            aid = -1
        ctx = it.get("context") if isinstance(it.get("context"), Mapping) else {}
        blob = f"{ctx.get('question','')} {ctx.get('answer_excerpt','')}"
        if gemini_fallback_heuristic:
            rid, conf = _heuristic_label(blob)
            err_note = str(last_err)[:200] if last_err else ""
            return {
                aid: (
                    rid,
                    conf,
                    f"gemini_fallback_heuristic_v1(after_timeout; {err_note})",
                )
            }
        raise RuntimeError(f"Gemini batch failed after retries: {last_err!r}") from last_err

    mid = max(1, len(batch) // 2)
    left = _gemini_resolve_batch(
        batch[:mid],
        model=model,
        base_timeout=base_timeout,
        max_retries=max_retries,
        backoff_sec=backoff_sec,
        gemini_fallback_heuristic=gemini_fallback_heuristic,
    )
    right = _gemini_resolve_batch(
        batch[mid:],
        model=model,
        base_timeout=base_timeout,
        max_retries=max_retries,
        backoff_sec=backoff_sec,
        gemini_fallback_heuristic=gemini_fallback_heuristic,
    )
    return {**left, **right}


def main() -> int:
    _load_workspace_dotenv()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, default=_DEFAULT_BUNDLE)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--provider", choices=("gemini", "heuristic"), default="heuristic")
    p.add_argument("--model", type=str, default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    p.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Base HTTP timeout in seconds for Gemini (sent as ms; min 10s server-side). Increases per retry.",
    )
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--max-retries", type=int, default=4)
    p.add_argument("--retry-backoff-sec", type=float, default=2.0)
    p.add_argument(
        "--gemini-fallback-heuristic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="On Gemini failure for a single row, use substring heuristic (default: on).",
    )
    args = p.parse_args()

    if not args.bundle.is_file():
        raise SystemExit(f"missing bundle: {args.bundle}")

    doc = json.loads(args.bundle.read_text(encoding="utf-8"))
    items = doc.get("items")
    if not isinstance(items, list):
        raise SystemExit("bundle.items must be a list")

    filled: Dict[int, Tuple[str, float, str]] = {}

    if args.provider == "heuristic":
        for it in items:
            if not isinstance(it, Mapping):
                continue
            try:
                aid = int(it.get("audit_id", -1))
            except (TypeError, ValueError):
                continue
            ctx = it.get("context") if isinstance(it.get("context"), Mapping) else {}
            blob = f"{ctx.get('question','')} {ctx.get('answer_excerpt','')}"
            rid, conf = _heuristic_label(blob)
            filled[aid] = (rid, conf, "heuristic_substring_v1")
    else:
        batch: List[Mapping[str, Any]] = []
        for it in items:
            if not isinstance(it, Mapping):
                continue
            batch.append(it)
            if len(batch) >= args.batch_size:
                part = _gemini_resolve_batch(
                    batch,
                    model=args.model,
                    base_timeout=args.timeout,
                    max_retries=args.max_retries,
                    backoff_sec=args.retry_backoff_sec,
                    gemini_fallback_heuristic=args.gemini_fallback_heuristic,
                )
                for aid, (rid, conf, src) in part.items():
                    filled[aid] = (rid, conf, src)
                batch = []
        if batch:
            part = _gemini_resolve_batch(
                batch,
                model=args.model,
                base_timeout=args.timeout,
                max_retries=args.max_retries,
                backoff_sec=args.retry_backoff_sec,
                gemini_fallback_heuristic=args.gemini_fallback_heuristic,
            )
            for aid, (rid, conf, src) in part.items():
                filled[aid] = (rid, conf, src)

    out_items: List[Any] = []
    for it in items:
        if not isinstance(it, Mapping):
            out_items.append(it)
            continue
        row = dict(it)
        try:
            aid = int(row.get("audit_id", -1))
        except (TypeError, ValueError):
            aid = -1
        human = dict(row.get("human") or {})
        if aid in filled:
            rid, conf, src = filled[aid]
            human["regime_id"] = rid
            human["confidence"] = conf
            human["notes"] = f"[AUTO_{args.provider.upper()}] {src}; not_human_audit."
        else:
            human["regime_id"] = "unknown"
            human["confidence"] = 0.2
            human["notes"] = f"[AUTO_{args.provider.upper()}] missing_batch_result; not_human_audit."
        row["human"] = human
        out_items.append(row)

    out_doc = copy.deepcopy(doc)
    out_doc["items"] = out_items
    out_doc["label_provenance"] = {
        "mode": f"auto_{args.provider}",
        "warning": "Automated fill (Gemini or heuristic). Replace with real human labels for ground truth.",
        "filled_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    out_doc["risk_note"] = {"b_track_only": True, "not_trading_trigger": True, "not_ground_truth": True}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output": str(args.output.as_posix()), "provider": args.provider},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
