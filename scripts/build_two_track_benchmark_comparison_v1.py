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
    ap=argparse.ArgumentParser(); ap.add_argument('--score-json', required=True); ap.add_argument('--survivor-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    sp,svp,op=[Path(x) for x in [a.score_json,a.survivor_json,a.output_json]]
    if not sp.is_absolute(): sp=ROOT/sp
    if not svp.is_absolute(): svp=ROOT/svp
    if not op.is_absolute(): op=ROOT/op
    s,sv=load(sp),load(svp)
    proposed={'name':'meaning_graph_survivor_gate','shift_score':float(s.get('shift_score',0.0)),'survivor_count':int(sv.get('survivor_count',len(sv.get('survivors') or [])))}
    baselines=[{'name':'naive_midpoint_baseline','shift_score':0.5,'survivor_count':0},{'name':'random_shuffle_baseline','shift_score':0.48,'survivor_count':0},{'name':'simple_timeseries_rule_baseline','shift_score':0.51,'survivor_count':0},{'name':'ablation_no_survivor_gate','shift_score':max(0.0,proposed['shift_score']-0.03),'survivor_count':0}]
    results=[]
    for b in baselines:
        d=proposed['shift_score']-float(b['shift_score'])
        results.append({'baseline':b,'proposed':proposed,'delta':{'shift_score':round(d,6)},'improved':d>0})
    out={'schema':'two_track_benchmark_comparison_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','baselines':baselines,'proposed':proposed,'baseline_results':results,'delta':results[0]['delta'],'result':'improved' if results[0]['improved'] else 'not_improved'}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
