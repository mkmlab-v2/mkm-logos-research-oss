$VaultRoot = 'G:\공유 드라이브\MKM_DATA_VAULT\vault'
$p = Split-Path -Parent $VaultRoot
Write-Host "VaultRoot: $VaultRoot"
Write-Host "Parent (MKM_DATA_VAULT): $p"
Write-Host "Test-Path parent: $(Test-Path -LiteralPath $p)"
Write-Host "Test-Path vault: $(Test-Path -LiteralPath $VaultRoot)"
