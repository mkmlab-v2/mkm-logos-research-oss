# Re-enables a minimal set of workspace automation tasks after quiet-mode disables.
# Does not require admin if tasks are owned by the current user.

param([switch]$WhatIf)

$ErrorActionPreference = "Continue"

$taskNames = @(
    '\Bitcoin-Ops-Phase1-Chain-Daily',
    '\Bitcoin-Ops-Phase1-Chain-Daily-Local',
    '\MKM-Ops-Phase1-Chain-Daily-V2',
    '\MKM-PreNews-Shadow-Daily',
    '\MKM-PreNews-Shadow-Health-Daily',
    '\Bitcoin-Fused-QuantPixel-SOP-Live-Daily',
    '\Bitcoin-Fused-QuantPixel-SOP-Strict-Check',
    '\Bitcoin-Runtime-Health-Check',
    '\Bitcoin-Runtime-Alert-Check',
    '\Bitcoin-WaitingQueue-BTCBinance-Daily-Strict',
    '\Bitcoin-WaitingQueue-DualMarket-Daily-Strict'
)

$ok = 0
$fail = New-Object System.Collections.Generic.List[string]

foreach ($tn in $taskNames) {
    if ($WhatIf) {
        Write-Host "[WhatIf] schtasks /Change /TN $tn /Enable"
        continue
    }
    schtasks.exe /Change /TN $tn /Enable 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $ok++
    } else {
        $fail.Add($tn)
    }
}

Write-Host ("enabled_ok={0} failed={1}" -f $ok, $fail.Count)
if ($fail.Count -gt 0) {
    Write-Host "Failed (missing name or access denied):" -ForegroundColor Yellow
    $fail | ForEach-Object { Write-Host "  $_" }
}
