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
    ap=argparse.ArgumentParser(); ap.add_argument('--fusion-report-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    fp,op=Path(a.fusion_report_json),Path(a.output_json)
    if not fp.is_absolute(): fp=ROOT/fp
    if not op.is_absolute(): op=ROOT/op
    f=load(fp)
    k=((f.get('tracks') or {}).get('K') or {})
    t=((f.get('tracks') or {}).get('T') or {})
    out={'schema':'two_track_fusion_brief_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','headline':'Two-track fusion status','cards':[{'id':'k_summary','value':k.get('summary',{})},{'id':'shift_score','value':t.get('shift_score',0.0)},{'id':'survivor_count','value':t.get('survivor_count',0)}],'storylines':['K-track narrative is isolated from trade trigger','T-track applies survivor filter and rollback gates'],'guardrail':'not_for_direct_trading_signal'}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
