@echo off
REM Golden-40 shard-1 on AUX (requires C:\workspace clone + Python).
cd /d C:\workspace
py scripts\run_nextgen_ng40_golden40_shard_eval_v1.py --shard-index 1 --shard-count 2 --match-active-caps --out-json Z:\nextgen_cpu_aux\ng40_golden40_shard1_v1_latest.json
pause
