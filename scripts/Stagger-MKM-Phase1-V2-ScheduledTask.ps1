# Stagger \MKM-Ops-Phase1-Chain-Daily-V2 away from 08:30 to reduce overlap with \Bitcoin-Ops-Phase1-Chain-Daily.
# Default new time: 09:20. Requires same privileges as schtasks /Change.
param(
    [string]$TaskName = "\MKM-Ops-Phase1-Chain-Daily-V2",
    [string]$NewStartTime = "09:20",
    [switch]$WhatIf
)
$ErrorActionPreference = "Stop"
if ($WhatIf) {
    Write-Host "[WhatIf] schtasks /Change /TN $TaskName /ST $NewStartTime  (daily trigger keeps /SC DAILY)"
    exit 0
}
schtasks.exe /Change /TN $TaskName /ST $NewStartTime
if ($LASTEXITCODE -ne 0) {
    throw "schtasks /Change failed (exit $LASTEXITCODE). Run elevated if access denied."
}
Write-Host "OK: $TaskName daily start set to $NewStartTime"
exit 0
