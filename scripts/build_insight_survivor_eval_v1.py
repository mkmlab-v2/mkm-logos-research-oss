#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def clamp(x): return max(0.0,min(1.0,float(x)))
def load(path):
    o=json.loads(path.read_text(encoding='utf-8'))
    return o if isinstance(o,dict) else {}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--insight-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ip,op=Path(a.insight_json),Path(a.output_json)
    if not ip.is_absolute(): ip=ROOT/ip
    if not op.is_absolute(): op=ROOT/op
    d=load(ip); cands=list(d.get('candidates') or [])
    rows=[]
    for i,c in enumerate(cands):
        hub=clamp(c.get('hub_score',0.0)); path=clamp(c.get('path_score',0.0)); cs=max(1,int(c.get('cluster_size',1)))
        dda=clamp(hub*0.45+path*0.35+min(1.0,cs/500.0)*0.2)
        fpc=clamp(1.0-(path*0.55+hub*0.25+min(1.0,cs/500.0)*0.2))
        wfr=clamp(path*0.6+hub*0.3+(1.0-fpc)*0.1)
        ci=clamp(dda*0.7+wfr*0.3)
        fusion=clamp(dda*0.4+wfr*0.3+(1.0-fpc)*0.2+ci*0.1)
        rows.append({'candidate_id':c.get('candidate_id',f'cand_{i+1:03d}'),'source_node_id':c.get('source_node_id',''),'drawdown_avoidance_score':dda,'false_positive_cost':fpc,'walkforward_repro_score':wfr,'ci_low_defense_contrib':ci,'fusion_candidate_score':fusion,'source_summary':c})
    doc={'schema':'insight_survivor_eval_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'T','rows':rows}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
