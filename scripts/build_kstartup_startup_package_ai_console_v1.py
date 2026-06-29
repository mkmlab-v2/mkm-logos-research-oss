#!/usr/bin/env python3
"""Generate F12 Console paste script for 창업패키지 PMS (logged-in Chrome)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/kstartup_startup_package_ai_paste_ready"
OUT_JS = ROOT / "scripts/kstartup_startup_package_ai_pms_console_v1.js"
OUT_META = ROOT / "reports/kstartup_startup_package_ai_console_latest.json"

FILES = [
    "plan_01_summary_paste.txt",
    "plan_02_market_problem_paste.txt",
    "plan_03_tech_roadmap_paste.txt",
    "plan_04_growth_funding_paste.txt",
    "plan_05_team_paste.txt",
    "plan_06_ai_talent_2p_paste.txt",
]


def _body(path: Path) -> str:
    t = path.read_text(encoding="utf-8")
    for prefix in ("[창업패키지", "[K-Startup"):
        if t.startswith(prefix):
            end = t.find("]\n\n")
            if end > 0:
                t = t[end + 3 :]
    return t.strip().replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def main() -> int:
    chunks: list[dict[str, str]] = []
    for fname in FILES:
        p = PASTE_DIR / fname
        if p.is_file():
            chunks.append({"file": fname, "text": _body(p)})

    chunks_json = json.dumps(chunks, ensure_ascii=False)
    js = f"""/**
 * 창업패키지 AI 인재 실증형 — PMS 빈 textarea 채움 (F12 Console)
 * 로그인된 Chrome · 사업신청 화면에서 실행 · 제출완료 누르지 말 것
 */
(function () {{
  const CHUNKS = {chunks_json};
  let seq = 0;
  const filled = [];
  const tas = [...document.querySelectorAll("textarea")].filter(
    (t) => t.id && !t.readOnly
  );
  for (const ta of tas) {{
    const cur = (ta.value || "").trim();
    if (cur.length > 30) continue;
    const text = CHUNKS[seq] ? CHUNKS[seq].text : "";
    if (!text) break;
    ta.focus();
    ta.value = text.slice(0, 12000);
    ta.dispatchEvent(new Event("input", {{ bubbles: true }}));
    ta.dispatchEvent(new Event("change", {{ bubbles: true }}));
    filled.push({{ id: ta.id, file: CHUNKS[seq].file, len: ta.value.length }});
    seq++;
  }}
  console.table(filled);
  alert(
    "textarea " +
      filled.length +
      "개 채움. 확인 후 임시저장만 누르세요. 제출완료는 직접."
  );
}})();
"""
    OUT_JS.write_text(js, encoding="utf-8")
    OUT_META.write_text(
        json.dumps(
            {"out_js": str(OUT_JS.relative_to(ROOT)).replace("\\", "/"), "chunks": len(chunks)},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(str(OUT_JS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
