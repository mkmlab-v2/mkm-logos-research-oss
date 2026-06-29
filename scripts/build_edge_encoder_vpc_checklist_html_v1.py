#!/usr/bin/env python3
"""Build operator HTML checklist from VPC deploy runbook [HYPO] B-track."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs/final/artifacts/edge_encoder_vpc_deploy_runbook_v1_latest.json"
OUT_HTML = ROOT / "reports/demo/edge_encoder_vpc_deploy_checklist_v1.html"
OUT_JSON = ROOT / "reports/edge_encoder_vpc_deploy_checklist_v1_latest.json"


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def render_html(doc: dict) -> str:
    phases_html = []
    for phase in doc.get("phases") or []:
        steps = "".join(f"<li><code>{_esc(s)}</code></li>" for s in phase.get("steps") or [])
        phases_html.append(
            f"<section><h3>{_esc(str(phase.get('id')))} · {_esc(str(phase.get('title')))}</h3><ol>{steps}</ol></section>"
        )
    gates = "".join(f"<li><code>{_esc(g)}</code></li>" for g in doc.get("human_gates") or [])
    verify = "".join(
        f'<li><code>{_esc(c)}</code></li>' for c in doc.get("verify_commands") or []
    )
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>Edge Encoder VPC Deploy Checklist</title>
<meta name="robots" content="noindex,nofollow">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
body{{font-family:Pretendard,system-ui,sans-serif;max-width:820px;margin:24px auto;padding:0 16px 40px;background:#0f1412;color:#e8ebe9;line-height:1.65}}
h1{{font-size:1.3rem}} h3{{font-size:1rem;margin:0 0 8px;color:#9fd4c4}}
section{{margin:14px 0;padding:14px 16px;border:1px solid rgba(255,255,255,.1);border-radius:10px;background:#151c19}}
code{{font-size:12px;word-break:break-all}}
.warn{{color:#e8c88a;font-size:13px;margin:8px 0}}
.tag{{display:inline-block;padding:2px 8px;border-radius:6px;background:#2a3530;font-size:12px;margin-right:6px}}
ol{{margin:0;padding-left:20px}} li{{margin:6px 0}}
</style></head><body>
<h1>Edge Encoder · Customer VPC Deploy Checklist</h1>
<p><span class="tag">[HYPO]</span><span class="tag">research_only</span><span class="tag">send_gate: HOLD</span></p>
<p class="warn">original_bulk_sent: false — wire만 교차. MASK 47% KPI와 합선 금지 (FAIL-COMP-004).</p>
<p class="warn">generated: <code>{_esc(str(doc.get('generated_at_utc')))}</code></p>
{''.join(phases_html)}
<section><h3>Human gates</h3><ul>{gates}</ul></section>
<section><h3>Verify commands</h3><ol>{verify}</ol></section>
<section><h3>One-click chain</h3><p><code>powershell -File scripts/Invoke-EdgeEncoderAirGapPoC_v1.ps1</code></p></section>
</body></html>
"""


def main() -> int:
    if not RUNBOOK.is_file():
        print(json.dumps({"ok": False, "error": f"missing {RUNBOOK}"}, ensure_ascii=False))
        return 1
    doc = json.loads(RUNBOOK.read_text(encoding="utf-8"))
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(render_html(doc), encoding="utf-8")
    summary = {
        "ok": True,
        "schema": "edge_encoder_vpc_deploy_checklist_v1",
        "html": str(OUT_HTML.relative_to(ROOT)).replace("\\", "/"),
        "runbook": str(RUNBOOK.relative_to(ROOT)).replace("\\", "/"),
        "phase_count": len(doc.get("phases") or []),
        "send_gate": doc.get("send_gate"),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
