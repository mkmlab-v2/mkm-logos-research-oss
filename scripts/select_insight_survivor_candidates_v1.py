#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def load(path):
    o=json.loads(path.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--eval-json', required=True); ap.add_argument('--output-json', required=True); ap.add_argument('--top-n', type=int, default=5); a=ap.parse_args()
    ep,op=Path(a.eval_json),Path(a.output_json)
    if not ep.is_absolute(): ep=ROOT/ep
    if not op.is_absolute(): op=ROOT/op
    d=load(ep); rows=list(d.get('rows') or [])
    rows.sort(key=lambda r: float(r.get('fusion_candidate_score',0.0)), reverse=True)
    surv=rows[:max(1,int(a.top_n))]
    doc={'schema':'insight_survivor_candidates_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'T','survivor_count':len(surv),'survivors':surv}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
