$ErrorActionPreference = "Stop"

$projectRoot = "C:\workspace\projects\bitcoin-trading"
$approvalPath = Join-Path $projectRoot "memory\v2\ops\execute_approval.json"

if (Test-Path $approvalPath) {
    Remove-Item $approvalPath -Force
    Write-Host "Execute approval revoked: $approvalPath"
} else {
    Write-Host "Execute approval file not found"
}
