#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(p):
    o=json.loads(p.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--brief-json', required=True); ap.add_argument('--output-json', required=True); ap.add_argument('--tone', default='executive'); a=ap.parse_args()
    bp,op=Path(a.brief_json),Path(a.output_json)
    if not bp.is_absolute(): bp=ROOT/bp
    if not op.is_absolute(): op=ROOT/op
    b=load(bp)
    out={'schema':'two_track_fusion_presentation_brief_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','tone':a.tone,'headline':b.get('headline','Two-track fusion status'),'priority_cards':b.get('cards',[]),'storylines':b.get('storylines',[]),'guardrail':b.get('guardrail','')}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
