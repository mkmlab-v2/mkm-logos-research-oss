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
    ap=argparse.ArgumentParser(); ap.add_argument('--insight-json', required=True); ap.add_argument('--survivor-json', required=True); ap.add_argument('--report-json', required=True); ap.add_argument('--viz-json', required=True); a=ap.parse_args()
    ip,sp,rp,vp=[Path(x) for x in [a.insight_json,a.survivor_json,a.report_json,a.viz_json]]
    if not ip.is_absolute(): ip=ROOT/ip
    if not sp.is_absolute(): sp=ROOT/sp
    if not rp.is_absolute(): rp=ROOT/rp
    if not vp.is_absolute(): vp=ROOT/vp
    i=load(ip); s=load(sp)
    cands=list(i.get('candidates') or [])
    surv=list(s.get('survivors') or [])
    report={'schema':'bible_meaning_knowledge_ip_report_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','purpose':'knowledge_ip_only','not_for_trading_signal':True,'summary':{'candidate_count':len(cands),'survivor_count':len(surv)},'storylines':[{'title':'Cross-reference cluster narrative','confidence':'medium'}]}
    viz={'schema':'bible_meaning_knowledge_ip_viz_v1','generated_at_utc':now(),'nodes':cands[:30],'edges':[]}
    rp.parent.mkdir(parents=True, exist_ok=True); vp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); vp.write_text(json.dumps(viz,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(str(rp)); print(str(vp)); return 0
if __name__=='__main__': raise SystemExit(main())
