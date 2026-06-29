#!/usr/bin/env python3
"""[HYPO] Azure OpenAI synthesis on Discovery Engine probe hits (generative ROI; no codec wire)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROBE_DEFAULT = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/ng40_de_probe_azure_openai_synthesis_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _azure_cfg() -> dict[str, str] | None:
    endpoint = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip().rstrip("/")
    api_key = (os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
    deployment = (
        os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
        or ""
    ).strip()
    if not endpoint or not api_key or not deployment:
        return None
    ver = (os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()
    dep = urllib.parse.quote(deployment, safe="")
    api_v = urllib.parse.quote(ver, safe="")
    url = f"{endpoint}/openai/deployments/{dep}/chat/completions?api-version={api_v}"
    return {"url": url, "api_key": api_key, "deployment": deployment}


def _hits_context(hits: list[dict[str, Any]], max_snippet_chars: int) -> str:
    parts: list[str] = []
    for i, h in enumerate(hits[:8], 1):
        title = str(h.get("title") or "")
        snips = h.get("snippets") or []
        snip = " ".join(str(s) for s in snips if s)[:max_snippet_chars]
        parts.append(f"[{i}] {title}\n{snip}")
    return "\n\n".join(parts)


def _chat(
    cfg: dict[str, str],
    messages: list[dict[str, str]],
    max_tokens: int,
    *,
    retries: int = 4,
    retry_sleep_s: float = 18.0,
) -> tuple[bool, str, str | None]:
    body = json.dumps(
        {
            "model": cfg["deployment"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
        }
    ).encode("utf-8")
    last_err: str | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            cfg["url"],
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "api-key": cfg["api_key"]},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                payload = json.loads(res.read().decode("utf-8"))
            text = str((payload.get("choices") or [{}])[0].get("message", {}).get("content") or "")
            return True, text.strip(), None
        except urllib.error.HTTPError as e:
            last_err = f"http_{e.code}:{e.read().decode('utf-8', errors='replace')[:200]}"
            if e.code == 429 and attempt + 1 < retries:
                time.sleep(retry_sleep_s * (attempt + 1))
                continue
            return False, "", last_err
        except Exception as e:
            last_err = f"{type(e).__name__}:{str(e)[:200]}"
            return False, "", last_err
    return False, "", last_err


def _extract_verse_refs(text: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(r"verse:([A-Za-z0-9_.]+)", text):
        found.append(m.group(1))
    for m in re.finditer(r"\b([1-3]?\s?[A-Za-z]+\.\s?\d+:\d+)\b", text):
        v = m.group(1).replace(" ", "")
        if v not in found:
            found.append(v)
    return found[:12]


def _synthesize_probe(
    probe: dict[str, Any],
    *,
    cfg: dict[str, str] | None,
    max_snippet_chars: int,
    max_tokens: int,
    dry_run: bool,
) -> dict[str, Any]:
    ctx = _hits_context(probe.get("hits") or [], max_snippet_chars)
    system = (
        "You are an MKM B-track research assistant. Output is [HYPO] staging only. "
        "Do NOT claim trading signals, Track A promotion, or clinical truth. "
        "Suggest biblical anchor candidates for human review only."
    )
    user = (
        f"Probe: {probe.get('probe_id')} ({probe.get('label_ko')})\n"
        f"Role: {probe.get('role')}\n"
        f"DE query: {probe.get('query')}\n\n"
        f"Discovery Engine snippets:\n{ctx}\n\n"
        "Respond in JSON only with keys: "
        "anchor_candidates (array of {label, rationale, confidence: low|medium}), "
        "verse_refs_guess (array of strings), "
        "human_review_note (one sentence Korean), "
        "non_gating_disclaimer (must mention NON_GATING)."
    )
    row: dict[str, Any] = {
        "probe_id": probe.get("probe_id"),
        "label_ko": probe.get("label_ko"),
        "hit_count": probe.get("hit_count"),
        "dry_run": dry_run,
    }
    if dry_run or not cfg:
        row["status"] = "dry_run_skipped"
        row["verse_refs_from_snippets"] = _extract_verse_refs(ctx)
        return row

    ok, text, err = _chat(
        cfg,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens,
    )
    row["azure_ok"] = ok
    if err:
        row["error"] = err
        row["status"] = "azure_error"
        return row
    row["raw_reply"] = text[:4000]
    try:
        # strip markdown fence if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned)
        row["synthesis"] = parsed
        row["status"] = "ok"
    except json.JSONDecodeError:
        row["synthesis"] = {"human_review_note": text[:500]}
        row["status"] = "ok_non_json"
    row["verse_refs_from_snippets"] = _extract_verse_refs(ctx)
    if row.get("synthesis"):
        vg = row["synthesis"].get("verse_refs_guess") or []
        row["verse_refs_merged"] = list(
            dict.fromkeys(list(vg) + row["verse_refs_from_snippets"])
        )[:16]
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe-json", type=Path, default=PROBE_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-probes", type=int, default=0, help="0 = all probes")
    ap.add_argument("--max-snippet-chars", type=int, default=600)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.probe_json.is_file():
        print(json.dumps({"error": "missing_probe", "path": str(args.probe_json)}))
        return 2

    _load_dotenv(ROOT / ".env")
    cfg = None if args.dry_run else _azure_cfg()
    if not args.dry_run and not cfg:
        print(
            json.dumps(
                {
                    "error": "missing_azure_openai_env",
                    "required": [
                        "AZURE_OPENAI_ENDPOINT",
                        "AZURE_OPENAI_API_KEY",
                        "AZURE_OPENAI_DEPLOYMENT",
                    ],
                }
            )
        )
        return 2

    probe_doc = json.loads(args.probe_json.read_text(encoding="utf-8-sig"))
    probes = list(probe_doc.get("probes") or [])
    if args.max_probes > 0:
        probes = probes[: args.max_probes]

    rows: list[dict[str, Any]] = []
    for i, p in enumerate(probes):
        if i > 0 and cfg and not args.dry_run:
            time.sleep(3.0)
        rows.append(
            _synthesize_probe(
                p,
                cfg=cfg,
                max_snippet_chars=args.max_snippet_chars,
                max_tokens=args.max_tokens,
                dry_run=args.dry_run,
            )
        )
    ok_n = sum(1 for r in rows if r.get("status") in ("ok", "ok_non_json"))

    out = {
        "schema": "ng40_de_probe_azure_openai_synthesis_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "gating_policy": "NON_GATING",
        "billing_surface": "azure_openai",
        "credit_note": "Consumes Azure Startup credits (not GCP App Builder trial)",
        "probe_pointer": str(args.probe_json.relative_to(ROOT)).replace("\\", "/"),
        "deployment": cfg["deployment"] if cfg else None,
        "dry_run": args.dry_run,
        "forbidden": [
            "auto_merge_into_ng40_codec",
            "auto_merge_into_lut_without_commander_signoff",
            "track_a_active_write",
        ],
        "human_workflow": [
            "Commander reviews synthesis per probe_id",
            "Map approved anchors to verse_decoded / concept_bridge",
            "Optional: build_archetype_prior_lut_draft --de-probe-json (staging only)",
        ],
        "syntheses": rows,
        "summary": {
            "probe_count": len(rows),
            "azure_ok_count": ok_n,
            "all_azure_ok": ok_n == len(rows) and len(rows) > 0,
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "azure_ok_count": ok_n,
                "probe_count": len(rows),
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
        )
    )
    return 0 if args.dry_run or ok_n == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
