# B-track: parity + hook sweep for ascii_compact (ops) vs o200k_tight (billing). Does not change .env permanently.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

py scripts/run_ijeoma_cjk_hook_billing_mode_compare_v1.py
exit $LASTEXITCODE
