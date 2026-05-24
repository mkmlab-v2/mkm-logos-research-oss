#!/usr/bin/env python3
"""Build personadiary B2C oracle-sphere draft HTML (UX shell only, FinOps stripped).

Reads graph topology for orb legend counts. Honest wire metrics stay in JSON meta only —
not rendered on personadiary public/demo (B2B: jemaai.cloud / a-codeai.com).

  py scripts/build_personadiary_logos_oracle_sphere_v6_draft_v1.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
GRAPH = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json"
DEFAULT_OUT = ROOT / "reports/personadiary/logos_oracle_sphere_v6_sync_draft.html"
PUBLIC_DEMO_OUT = ROOT / "projects/no1kmedi/public/personadiary-concept-demo.html"
HYPO_BANNER = (
    '<div role="note" style="background:#422006;color:#fde68a;text-align:center;'
    "padding:0.55rem 1rem;font-size:0.72rem;font-family:ui-monospace,monospace;"
    'border-bottom:1px solid rgba(251,191,36,0.35)">'
    "[HYPO] 콘셉트 데모 · 의료·투자·처방 조언 아님 · 오픈베타 미리보기 · research_only"
    "</div>"
)
V6_URL = "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1"

KIND_COLORS = {
    "verse": "#64d2ff",
    "theme": "#ffd60a",
    "regime": "#5e5ce6",
    "era": "#bf5af2",
}
KIND_RGB = {
    "verse": "100, 210, 255",
    "theme": "255, 214, 10",
    "regime": "94, 92, 230",
    "era": "191, 90, 242",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_html(*, nodes: int, edges: int, gen: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>personadiary.com | 마음의 구슬 (오픈베타 데모)</title>
  <meta name="description" content="B2C 성찰·일기 콘셉트 데모. 인프라·임상 지표 없음. [HYPO] research_only." />
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Noto+Sans+KR:wght@400;600&display=swap" rel="stylesheet" />
  <style>
    body {{ font-family: Inter, 'Noto Sans KR', sans-serif; background: #030712; color: #e2e8f0; }}
    .glass {{ background: rgba(9,13,22,.72); border: 1px solid rgba(255,255,255,.08); backdrop-filter: blur(16px); }}
    .orb-wrap {{ animation: float 6s ease-in-out infinite; }}
    @keyframes float {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-8px)}} }}
    .moment-card {{ transition: transform 0.25s ease, border-color 0.25s ease; }}
    .moment-card:hover {{ transform: perspective(600px) rotateX(4deg) rotateY(-3deg); border-color: rgba(99,102,241,0.45); }}
    .moment-card:active {{ transform: perspective(600px) rotateX(2deg) scale(0.98); }}
  </style>
</head>
<body class="min-h-screen">
  <header class="glass sticky top-0 z-10 px-6 py-4 flex justify-between items-center flex-wrap gap-2">
    <div>
      <span class="text-lg font-semibold">personadiary.com</span>
      <span class="text-[10px] text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded ml-2">open-beta</span>
    </div>
    <a class="text-sm text-slate-400 hover:text-white" href="{V6_URL}" target="_blank" rel="noopener">학술 관측 본선 (별도) ↗</a>
  </header>

  <main class="max-w-6xl mx-auto px-4 py-10 space-y-10">
    <section class="text-center space-y-3">
      <h1 class="text-3xl md:text-4xl font-bold text-white">오늘의 마음을, 빛의 구슬에 남기다</h1>
      <p class="text-slate-400 text-sm max-w-xl mx-auto">
        평온을 돕는 가이드형 성찰 셸 · 처방·투자·임상 판정 없음 ·
        <a class="text-indigo-400 underline" href="/">홈으로</a>
      </p>
    </section>

    <section class="grid lg:grid-cols-2 gap-8">
      <div class="glass rounded-3xl p-6 flex flex-col items-center orb-wrap">
        <canvas id="orb" width="320" height="320" class="rounded-full cursor-pointer" aria-label="마음의 구슬 파티클"></canvas>
        <div class="grid grid-cols-4 gap-2 mt-4 text-[10px] w-full max-w-sm text-slate-400">
          <span><i style="background:{KIND_COLORS['verse']}" class="inline-block w-2 h-2 rounded-full"></i> 말씀</span>
          <span><i style="background:{KIND_COLORS['theme']}" class="inline-block w-2 h-2 rounded-full"></i> 주제</span>
          <span><i style="background:{KIND_COLORS['regime']}" class="inline-block w-2 h-2 rounded-full"></i> 흐름</span>
          <span><i style="background:{KIND_COLORS['era']}" class="inline-block w-2 h-2 rounded-full"></i> 시대</span>
        </div>
        <p id="orbStatus" class="text-xs text-indigo-300 mt-3">호흡과 함께 · 준비됨</p>
        <button id="toneToggle" type="button" class="mt-4 text-xs px-4 py-2 rounded-full border border-white/15 hover:border-emerald-500/40 text-slate-300">
          마음 호흡 톤 켜기
        </button>
      </div>

      <div class="space-y-4">
        <div class="glass rounded-2xl p-5 space-y-3">
          <p class="text-xs text-slate-500">오늘의 순간 카드</p>
          <button type="button" class="moment-card w-full text-left text-xs p-3 rounded-xl border border-white/10" data-q="transition">
            큰 전환 앞 — 마음을 가볍게 정리하고 싶을 때
          </button>
          <button type="button" class="moment-card w-full text-left text-xs p-3 rounded-xl border border-white/10" data-q="crossroads">
            갈림길 — 차분히 선택의 이유를 적어 볼 때
          </button>
          <button type="button" class="moment-card w-full text-left text-xs p-3 rounded-xl border border-white/10" data-q="gratitude">
            오늘 하루 — 감사한 순간 세 가지
          </button>
          <textarea id="query" class="w-full h-20 rounded-xl bg-slate-950/60 border border-white/10 p-3 text-sm" placeholder="지금 마음을 한두 문장으로 적어 주세요…"></textarea>
          <button id="ignite" type="button" class="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-emerald-600 text-sm font-semibold">
            구슬에 마음 남기기
          </button>
        </div>
        <div class="glass rounded-2xl p-4 text-[11px] space-y-2 text-slate-400">
          <p class="text-slate-300 font-medium text-xs">마음돌봄 셸</p>
          <p>이 화면은 <strong class="text-slate-200">시각·청각 리플렉션</strong>만 제공합니다. 일기 저장·결제·임상 연동은 오픈베타 범위 밖입니다.</p>
          <p class="text-slate-500">인프라·압축·거버넌스 수치는 personadiary에 노출하지 않습니다 (B2B: jema-ai.com · jemaai.cloud).</p>
        </div>
      </div>
    </section>

    <section id="result" class="hidden glass rounded-3xl p-6 space-y-4">
      <p class="text-xs text-amber-200/80">[HYPO] · research_only · 투자·의료·처방 조언이 아닙니다.</p>
      <p id="resultText" class="text-sm text-slate-300 leading-relaxed"></p>
      <p class="text-[10px] text-slate-500">데모 서사만 표시됩니다. 실제 상담·진단·매매 신호와 연결되지 않습니다.</p>
    </section>
  </main>

  <footer class="text-center text-[10px] text-slate-600 py-8 px-4">
    personadiary B2C shell · generated {gen} · builder: build_personadiary_logos_oracle_sphere_v6_draft_v1.py
  </footer>

  <script>
    const COLORS = {json.dumps(KIND_RGB)};
    const PRESET_TEXT = {{
      transition: '큰 변화가 다가올 때, 두려움보다 숨 고르기를 먼저 적어 봅니다.',
      crossroads: '갈림길에서 각 선택이 나에게 주는 평온과 부담을 나란히 적어 봅니다.',
      gratitude: '오늘 고마웠던 순간 세 가지를 짧게 적어 마음을 정리합니다.'
    }};
    const canvas = document.getElementById('orb');
    const ctx = canvas.getContext('2d');
    const cats = ['verse','theme','regime','era'];
    const N = 120, R = 95, F = 220;
    const pts = Array.from({{length:N}}, (_,i) => {{
      const t = Math.random()*Math.PI*2, p = Math.acos(Math.random()*2-1);
      const c = cats[i%4];
      return {{x:R*Math.sin(p)*Math.cos(t), y:R*Math.sin(p)*Math.sin(t), z:R*Math.cos(p), c}};
    }});
    function rot() {{
      const s = 0.004, cx=Math.cos(s), sx=Math.sin(s), cy=Math.cos(s*1.3), sy=Math.sin(s*1.3);
      pts.forEach(p => {{
        let x1=p.x*cy-p.z*sy, z1=p.z*cy+p.x*sy, y2=p.y*cx-z1*sx, z2=z1*cx+p.y*sx;
        p.x=x1; p.y=y2; p.z=z2;
      }});
    }}
    function draw() {{
      ctx.clearRect(0,0,320,320);
      rot();
      const sorted = [...pts].sort((a,b)=>b.z-a.z);
      sorted.forEach(p => {{
        const sc = F/(F+p.z), x=p.x*sc+160, y=p.y*sc+160, sz=Math.max(0.6,(R+p.z)/R*2);
        ctx.beginPath(); ctx.arc(x,y,sz,0,Math.PI*2);
        const a = Math.max(0.15,(p.z+R)/(2*R));
        ctx.fillStyle = 'rgba(' + COLORS[p.c] + ',' + a + ')';
        ctx.fill();
      }});
      requestAnimationFrame(draw);
    }}
    draw();

    let audioCtx = null, toneOsc = null, toneGain = null, toneOn = false;
    document.getElementById('toneToggle').addEventListener('click', async function() {{
      const btn = this;
      if (toneOn && audioCtx) {{
        toneGain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
        setTimeout(() => {{ try {{ toneOsc.stop(); }} catch(e) {{}} toneOn = false; btn.textContent = '마음 호흡 톤 켜기'; }}, 450);
        return;
      }}
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') await audioCtx.resume();
      toneOsc = audioCtx.createOscillator();
      toneGain = audioCtx.createGain();
      toneOsc.type = 'sine';
      toneOsc.frequency.value = 174;
      toneGain.gain.value = 0.0001;
      toneOsc.connect(toneGain);
      toneGain.connect(audioCtx.destination);
      toneOsc.start();
      toneGain.gain.exponentialRampToValueAtTime(0.04, audioCtx.currentTime + 1.2);
      toneOn = true;
      btn.textContent = '마음 호흡 톤 끄기';
      document.getElementById('orbStatus').textContent = '부드러운 톤 · 호흡에 맞춰';
    }});

    document.querySelectorAll('[data-q]').forEach(btn => btn.addEventListener('click', () => {{
      document.getElementById('query').value = PRESET_TEXT[btn.dataset.q] || '';
    }}));
    document.getElementById('ignite').addEventListener('click', () => {{
      const q = document.getElementById('query').value.trim();
      if (!q) return;
      document.getElementById('orbStatus').textContent = '마음을 담는 중…';
      setTimeout(() => {{
        document.getElementById('orbStatus').textContent = '오늘의 빛 · 기록됨 (데모)';
        const el = document.getElementById('result');
        el.classList.remove('hidden');
        document.getElementById('resultText').textContent =
          '데모 성찰: "' + q.slice(0, 120) + (q.length > 120 ? '…' : '') + '" — ' +
          '구슬이 오늘의 감정 결을 부드럽게 비춰 주었습니다. 이 문장은 저장되지 않으며, ' +
          '의료·투자·처방 판정과 무관한 미리보기입니다.';
        el.scrollIntoView({{behavior:'smooth'}});
      }}, 1200);
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    poc = _load_json(POC) if POC.is_file() else {}
    graph = _load_json(GRAPH) if GRAPH.is_file() else {}
    hm = poc.get("wire", {}).get("honest_metrics", {})
    nodes = graph.get("node_count") or len(graph.get("nodes") or []) or 72
    edges = graph.get("edge_count") or len(graph.get("edges") or []) or 99
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_path = DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = _render_html(nodes=nodes, edges=edges, gen=gen)
    out_path.write_text(html, encoding="utf-8")
    public_html = html.replace(
        '<body class="min-h-screen">',
        f'<body class="min-h-screen">\n  {HYPO_BANNER}',
        1,
    )
    PUBLIC_DEMO_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_DEMO_OUT.write_text(public_html, encoding="utf-8")
    meta = {
        "schema": "personadiary_logos_oracle_sphere_v6_draft_v1",
        "generated_at_utc": gen,
        "b2c_ui": {
            "finops_panel_stripped": True,
            "clinical_copy_stripped": True,
            "audio_tone_shell": True,
            "moment_cards": True,
        },
        "out_html": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        "public_demo_html": str(PUBLIC_DEMO_OUT.relative_to(ROOT)).replace("\\", "/"),
        "v6_url": V6_URL,
        "honest_metrics_internal_only": hm,
        "graph_nodes": nodes,
        "graph_edges": edges,
        "ok": True,
    }
    meta_path = ROOT / "reports/personadiary/logos_oracle_sphere_v6_sync_draft_latest.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
