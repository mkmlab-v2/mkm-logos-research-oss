@echo off
REM AUX PC: start RTT (19876) + P1 (19877) in separate windows. NG40 shard is manual/long-run.
cd /d Z:\nextgen_cpu_aux
start "MKM-RTT-19876" cmd /k py run_rtt_server_standalone.py --port 19876
start "MKM-P1-19877" cmd /k py run_p1_server_standalone.py --port 19877
echo Started RTT and P1 servers. For Golden-40 shard-1 run RUN_NG40_SHARD_ON_AUX.cmd in a third window.
pause
