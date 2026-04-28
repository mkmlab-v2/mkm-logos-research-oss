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
    ap=argparse.ArgumentParser(); ap.add_argument('--score-json', required=True); ap.add_argument('--survivor-json', required=True); ap.add_argument('--qa-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    sp,svp,qp,op=[Path(x) for x in [a.score_json,a.survivor_json,a.qa_json,a.output_json]]
    for name,p in [('sp',sp),('svp',svp),('qp',qp),('op',op)]:
        if not p.is_absolute():
            if name=='sp': sp=ROOT/p
            elif name=='svp': svp=ROOT/p
            elif name=='qp': qp=ROOT/p
            else: op=ROOT/p
    s,sv,q=load(sp),load(svp),load(qp)
    surv=list(sv.get('survivors') or [])
    first=surv[0] if surv else {}
    out={'schema':'two_track_academic_submission_packet_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','sources':{'score_json':str(sp),'survivor_json':str(svp),'qa_json':str(qp)},'abstract_scaffold':{'problem':'Overfitting risk in meaning-rich signals','method':'Two-track + survivor + rollback','result':f"shift_score={float(s.get('shift_score',0.0)):.4f}, survivor_count={len(surv)}",'claim_boundary':'research only / public-safe boundary'},'experiment_table':[{'metric':'shift_score','value':float(s.get('shift_score',0.0)),'source':str(sp)},{'metric':'survivor_count','value':len(surv),'source':str(svp)},{'metric':'ci_low_defense_contrib','value':float(first.get('ci_low_defense_contrib',0.0)),'source':str(svp)}],'falsification_checklist':[{'id':'F1','status':'pending'},{'id':'F2','status':'pending'},{'id':'F3','status':'pending'},{'id':'F4','status':'pending'},{'id':'F5','status':'in_progress'}],'defense_evidence_contract':dict(q.get('defense_prompt_policy') or {})}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
