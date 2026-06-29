#!/usr/bin/env python3
"""One-page brief: Kaggle v28 smoke + NIM Logos + local adapter infer ([HYPO] research_only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports/nemotron_parallel_research_brief_v1_latest.json"
OUT_MD = ROOT / "reports/nemotron_parallel_research_brief_v1_latest.md"

POINTERS = {
    "kaggle_smoke_gate": ROOT / "reports/kaggle_nemotron_fast_smoke_gate_v28_latest.json",
    "kaggle_resume": ROOT / "reports/kaggle_nemotron_resume_latest.json",
    "submission_manifest": ROOT / "reports/kaggle_nemotron_smoke_download_latest.json",
    "nim_logos": ROOT / "reports/nim_logos_research_handoff_v1_latest.json",
    "v28_infer": ROOT / "reports/nemotron_v28_adapter_inference_smoke_v1_latest.json",
}


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parts = {k: _load(p) for k, p in POINTERS.items()}
    missing = [k for k, v in parts.items() if v is None]
    if missing:
        print(f"[ERROR] missing inputs: {missing}", flush=True)
        return 1

    gate = parts["kaggle_smoke_gate"]
    nim = parts["nim_logos"]
    infer = parts["v28_infer"]
    nim_text = ((nim.get("chat") or {}).get("text") or "")[:800]
    logos_final_action = "WATCH" if "Final Action: WATCH" in nim_text else "unknown"

    doc = {
        "schema": "nemotron_parallel_research_brief_v1",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "research_only",
        "research_only": True,
        "wired_into_train": False,
        "track_wall": "no_track_a_live_auto_merge",
        "allow_competition_submit": False,
        "summary": {
            "kaggle_v28_smoke": gate.get("gate_status"),
            "nim_logos_ok": (nim.get("chat") or {}).get("ok"),
            "logos_final_action": logos_final_action,
            "logos_gating": nim.get("gating") or "NON_GATING",
            "v28_local_infer": infer.get("status"),
            "v28_infer_mode": infer.get("infer_mode"),
            "expansion_stance": "HOLD",
            "fused_ops_ok": (
                gate.get("gate_status") == "pass"
                and (nim.get("chat") or {}).get("ok") is True
                and infer.get("status") == "pass"
            ),
        },
        "artifacts": {
            "submission_zip": gate.get("artifacts", {}).get("submission_zip"),
            "submission_sha256": gate.get("artifacts", {}).get("sha256"),
            "nim_logos_json": str(POINTERS["nim_logos"].relative_to(ROOT)),
            "nim_logos_md": "reports/nim_logos_research_handoff_v1_latest.md",
            "v28_infer_json": str(POINTERS["v28_infer"].relative_to(ROOT)),
        },
        "blocked_until": gate.get("blocked_until"),
        "next_lane": gate.get("next_lane"),
        "operator_paste": "reports/nvidia_hybrid_operator_paste_v1_latest.txt",
        "hybrid_lab_status": "reports/hybrid_ai_lab_status_v1_latest.json",
        "inputs_loaded": list(parts.keys()),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = f"""# Nemotron parallel research brief v1

**generated:** {doc["finished_at_utc"]} · `[HYPO]` · `research_only` · Track A/실매매 합선 없음

## Summary

| Track | Status | Evidence |
|-------|--------|----------|
| Kaggle v28 fast smoke | **{gate.get("gate_status")}** | T4 x2 · exit 0 · `submission_v28_fast_smoke.zip` |
| NIM Logos handoff | **{"ok" if doc["summary"]["nim_logos_ok"] else "fail"}** | `{doc["artifacts"]["nim_logos_json"]}` |
| v28 adapter infer | **{infer.get("status")}** | mode=`{infer.get("infer_mode", "local")}` · `{infer.get("base_model")}` |
| Logos Final Action | **{logos_final_action}** | `{nim.get("gating") or "NON_GATING"}` · 매매 GO 없음 |

## Operator sync (weekly · no Track A wire)

- **Final Action:** `{logos_final_action}` — AI·반도체·교역 허브 **관측만**; Logos 단독 트리거 없음
- **Paste SSOT:** `reports/nvidia_hybrid_operator_paste_v1_latest.txt`
- **Lab status:** `reports/hybrid_ai_lab_status_v1_latest.json`
- **expansion_stance:** HOLD (RunPod / Kaggle 30B full → Innovation Lab)

## NIM Logos (excerpt)

{nim_text}

## v28 infer (preview)

{infer.get("response_preview", "")[:400]}

## Blocked

- RunPod / Kaggle 30B full → Innovation Lab GPU approval
- Competition Submit → human gate

## Paths

- Gate: `reports/kaggle_nemotron_fast_smoke_gate_v28_latest.json`
- Brief JSON: `reports/nemotron_parallel_research_brief_v1_latest.json`
- Vault mirror: `…/btrack_artifacts_verified/nemotron_parallel_research_brief_v1/`
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(f"[OK] {OUT_JSON}")
    print(f"[OK] {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
