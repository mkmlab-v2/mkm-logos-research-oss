# Mirror MAX_HYPO sandbox closure artifacts to MKM_DATA_VAULT (optional G: mount).
param(
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"

$vaultBase = Get-ChildItem -Path "G:\" -Directory -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "vault" -and $_.FullName -match "MKM_DATA_VAULT" } |
    Select-Object -First 1

if (-not $vaultBase) {
    Write-Host "VAULT_SKIP: G: MKM_DATA_VAULT not mounted"
    exit 0
}

$dest = Join-Path $vaultBase.FullName "max_hypo_unbound_verified"
New-Item -ItemType Directory -Path $dest -Force | Out-Null

$rels = @(
    "experiments/max_hypo_unbound/results/max_hypo_recommended_tier_manifest_v1.json",
    "experiments/max_hypo_unbound/results/max_hypo_t10_shadow_eval_v1_latest.json",
    "experiments/max_hypo_unbound/results/max_theory_unbound_simulation_v1_latest.json",
    "reports/max_hypo_sandbox_closure_tradeoff_v1.md",
    "reports/max_hypo_recommended_tier_manifest_summary_v1.md"
)

$copied = @()
foreach ($rel in $rels) {
    $src = Join-Path $WorkspaceRoot ($rel -replace "/", "\")
    if (Test-Path -LiteralPath $src) {
        $leaf = Split-Path $src -Leaf
        Copy-Item -LiteralPath $src -Destination (Join-Path $dest $leaf) -Force
        $copied += $leaf
    }
}

$summary = [ordered]@{
    executed_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    target_root     = $dest
    copied_count    = $copied.Count
    copied_files    = $copied
}
$summaryPath = Join-Path $dest "_push_summary_latest.json"
($summary | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $summaryPath -Encoding UTF8
Write-Host "VAULT_OK copied=$($copied.Count) target=$dest"
