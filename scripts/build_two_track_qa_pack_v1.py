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
    ap=argparse.ArgumentParser(); ap.add_argument('--presenter-notes-json', required=True); ap.add_argument('--output-json', required=True); a=ap.parse_args()
    ip,op=Path(a.presenter_notes_json),Path(a.output_json)
    if not ip.is_absolute(): ip=ROOT/ip
    if not op.is_absolute(): op=ROOT/op
    d=load(ip); notes=list(d.get('notes_180s') or [])
    qna=[]
    for n in notes:
        aud=n.get('audience','general')
        qna.append({'audience':aud,'items':[{'q':'How do you avoid overfitting?','a':'Survivor + falsification + rollback.','evidence':{'source_artifact':'two_track_falsification_suite_latest.json','metric_value':'pending','as_of_utc':now(),'rollback_rule':'if gate fails then rollback','gate_eval':{'pass':False,'should_trade':False,'rollback':True,'reasons':['missing_gate']}}}]})
    out={'schema':'two_track_qa_pack_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'K','defense_prompt_policy':{'require_evidence_fields':['source_artifact','metric_value','as_of_utc','rollback_rule','gate_eval']},'audience_qna':qna}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
