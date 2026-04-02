# Tier S: memory/ 일부 -> MKM_DATA_VAULT (shared_mkm_vault 접점 제외 필수)
# shared_mkm_vault -> G:\...\vault 마운트 포인트이므로 Copy-Item -Recurse 금지 (무한 확장)
# 사용: .\scripts\push_workspace_memory_tier_s_to_vault.ps1
#       .\scripts\push_workspace_memory_tier_s_to_vault.ps1 -WhatIf

param(
    [string]$VaultRoot = "G:\공유 드라이브\MKM_DATA_VAULT\vault",
    [string]$MemoryRoot = "C:\workspace\memory",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path -LiteralPath $MemoryRoot)) {
    Write-Warning "memory 없음: $MemoryRoot"
    exit 1
}
# 한글 경로: LiteralPath로 해석해 FullName 고정 (robocopy 인자 깨짐 방지)
$VaultRoot = (Get-Item -LiteralPath $VaultRoot).FullName

$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$dest = Join-Path $VaultRoot "workspace_memory_tier_s_$stamp"

if ($WhatIf) {
    Write-Host "[WhatIf] Would create: $dest" -ForegroundColor Yellow
    exit 0
}

New-Item -ItemType Directory -Path $dest -Force | Out-Null

# 1) 단일 파일
Copy-Item -LiteralPath (Join-Path $MemoryRoot "ATHENA_SOVEREIGN_VERSION_DOC_INDEX_2026-03-19.md") `
    -Destination (Join-Path $dest "ATHENA_SOVEREIGN_VERSION_DOC_INDEX_2026-03-19.md") -Force

# 2) obsidian_vault: 접점 shared_mkm_vault 제외 + 접점 무시(/XJ)
$obsSrc = (Get-Item -LiteralPath (Join-Path $MemoryRoot "obsidian_vault")).FullName
$obsDst = (New-Item -ItemType Directory -Path (Join-Path $dest "obsidian_vault") -Force).FullName
& robocopy.exe $obsSrc $obsDst /E /XJ /XD shared_mkm_vault /R:2 /W:2 /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) {
    throw "robocopy obsidian_vault failed exit=$LASTEXITCODE"
}

# 3) 나머지 (접점 없음)
foreach ($d in @("archive", "evolution_logs", "lens_biblical_insight")) {
    $from = Join-Path $MemoryRoot $d
    Copy-Item -LiteralPath $from -Destination (Join-Path $dest $d) -Recurse -Force
}

$manifest = @"
workspace_memory Tier S backup (junction-safe)
generated_utc: $(Get-Date -Format "o")
source_root: $MemoryRoot
dest_root: $dest
included:
  - ATHENA_SOVEREIGN_VERSION_DOC_INDEX_2026-03-19.md
  - obsidian_vault/ via robocopy /E /XJ /XD shared_mkm_vault
  - archive/, evolution_logs/, lens_biblical_insight/
excluded:
  - obsidian_vault\shared_mkm_vault (mount -> MKM_DATA_VAULT\vault; recursive copy would duplicate entire vault)
notes:
  - If an older workspace_memory_tier_s_* folder exists from a bad Copy-Item run, delete it from Drive when unlocked.
"@

Set-Content -Path (Join-Path $dest "BACKUP_MANIFEST.txt") -Value $manifest -Encoding UTF8

Write-Host ">>> Tier S backup done: $dest" -ForegroundColor Green
exit 0
