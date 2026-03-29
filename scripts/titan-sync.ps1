# 최신 MASTER_SITREP → MKM_DATA_VAULT 공유 Vault로 복사 (원클릭 보급)
# 사용: .\scripts\titan-sync.ps1
#       .\scripts\titan-sync.ps1 -WhatIf
#       .\scripts\titan-sync.ps1 -SkipLocalBackup
# 이중화: 기본 F:\BACKUP\sitrep (실패 시 경고만, Vault 성공은 유지)
# 참조: .cursorrules §0.0.1 MASTER_SITREP
# 편집 시: UTF-8 with BOM으로 저장 (PS 5.1에서 한글 경로 리터럴 깨짐 방지)

param(
    [string]$SourceDir = "C:\workspace\docs\final",
    [string]$VaultRoot = "G:\공유 드라이브\MKM_DATA_VAULT\vault",
    [string]$SubFolder = "sitrep",
    [string]$LocalBackupDir = "F:\BACKUP\sitrep",
    [switch]$SkipLocalBackup,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceDir)) {
    Write-Warning "소스 없음: $SourceDir"
    exit 1
}

$latest = Get-ChildItem -LiteralPath $SourceDir -Filter "MASTER_SITREP_*.md" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    Write-Warning "MASTER_SITREP_*.md 없음: $SourceDir"
    exit 1
}

# Vault 루트는 $VaultRoot(…\vault)의 부모 = MKM_DATA_VAULT (한글 경로 한 곳만 param 기본값)
$mkmDataVaultRoot = Split-Path -Parent $VaultRoot
$vaultOk = Test-Path -LiteralPath $mkmDataVaultRoot
if (-not $vaultOk) {
    if ($WhatIf) {
        Write-Warning "MKM_DATA_VAULT 없음(WhatIf). 실제 복사 시 G: 매핑 필요."
    } else {
        Write-Warning "MKM_DATA_VAULT 없음. G: 매핑 또는 create_mkm_data_vault_structure.ps1 확인."
        exit 1
    }
}

$destDir = Join-Path $VaultRoot $SubFolder
if (-not (Test-Path -LiteralPath $destDir)) {
    if ($WhatIf) {
        Write-Host "[WhatIf] 디렉터리 생성: $destDir" -ForegroundColor Yellow
    } else {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
}

$destFile = Join-Path $destDir $latest.Name

Write-Host ">>> TITAN 보급" -ForegroundColor Cyan
Write-Host "   원본: $($latest.FullName) (LastWrite: $($latest.LastWriteTime))" -ForegroundColor Gray
Write-Host "   대상: $destFile" -ForegroundColor Gray

if ($WhatIf) {
    Write-Host "[WhatIf] 복사 생략." -ForegroundColor Yellow
    exit 0
}

Copy-Item -LiteralPath $latest.FullName -Destination $destFile -Force
Write-Host ">>> 보급 완료: $($latest.Name) → Vault\$SubFolder" -ForegroundColor Green

if (-not $SkipLocalBackup) {
    try {
        if (-not (Test-Path -LiteralPath $LocalBackupDir)) {
            New-Item -ItemType Directory -Path $LocalBackupDir -Force | Out-Null
        }
        $localDest = Join-Path $LocalBackupDir $latest.Name
        Copy-Item -LiteralPath $latest.FullName -Destination $localDest -Force
        Write-Host ">>> 로컬 이중화: $localDest" -ForegroundColor Green
    } catch {
        Write-Warning "로컬 백업 실패(F: 미연결·권한 등). Vault 보급은 완료됨: $_"
    }
}

exit 0
