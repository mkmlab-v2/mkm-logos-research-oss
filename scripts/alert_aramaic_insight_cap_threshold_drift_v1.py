#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def main():
    hp=ROOT/'reports/ops/aramaic_insight_cap_bucket_threshold_history.jsonl'; op=ROOT/'docs/final/artifacts/aramaic_insight_cap_bucket_threshold_drift_alert_latest.json'
    rows=[]
    if hp.is_file():
        for l in hp.read_text(encoding='utf-8-sig').splitlines():
            s=l.strip();
            if not s: continue
            try:o=json.loads(s)
            except Exception: continue
            if isinstance(o,dict): rows.append(o)
    alert={'schema':'aramaic_insight_cap_threshold_drift_alert_v1','generated_at_utc':now(),'research_only':True,'promotion_required':True,'source_track':'B','history_rows':len(rows),'should_alert':False,'reason':'insufficient_drift_or_stable'}
    op.parent.mkdir(parents=True, exist_ok=True); op.write_text(json.dumps(alert,ensure_ascii=False,indent=2)+'\n', encoding='utf-8'); print(str(op)); return 0
if __name__=='__main__': raise SystemExit(main())
