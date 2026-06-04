@echo off
REM Run on AUX PC (DESKTOP-AP1DC83). Requires Python on aux.
cd /d Z:\nextgen_cpu_aux
py run_rtt_server_standalone.py --port 19876
pause
