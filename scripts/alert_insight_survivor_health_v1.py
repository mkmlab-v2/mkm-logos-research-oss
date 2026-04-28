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
    ap=argparse.ArgumentParser(); ap.add_argument('--survivor-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    sp,op=Path(a.survivor_json),Path(a.output_json)
    if not sp.is_absolute(): sp=ROOT/sp
    if not op.is_absolute(): op=ROOT/op
    d=load(sp); surv=list(d.get('survivors') or [])
    mean=(sum(float(x.get('fusion_candidate_score',0.0)) for x in surv)/max(1,len(surv)))
    alert={'schema':'insight_survivor_health_alert_v1','generated_at_utc':now(),'source_track':'T','research_only':True,'promotion_required':True,'should_alert':False,'reason':'stable_or_insufficient_history','latest':{'survivor_count':len(surv),'survivor_mean_score':round(mean,6)}}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(alert,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
