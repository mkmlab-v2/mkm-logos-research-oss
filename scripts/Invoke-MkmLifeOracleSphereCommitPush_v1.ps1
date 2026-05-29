#Requires -Version 5.1
<#
.SYNOPSIS
  Commit staged mkm-life oracle-sphere changes, push submodule + monorepo probe/submodule bump.

.NOTES
  Run from Cursor terminal if agent git commit is blocked by pre_shell_guard hook.
#>
param(
    [switch]$SkipMonorepo,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = "C:\workspace"
$mkmLife = Join-Path $repoRoot "projects\mkm\mkm-life"

function Invoke-Git {
    param([string]$Cwd, [string[]]$GitArgs)
    $display = "git -C `"$Cwd`" $($GitArgs -join ' ')"
    if ($DryRun) {
        Write-Host "[DRY] $display"
        return
    }
    & git -C $Cwd @GitArgs
    if ($LASTEXITCODE -ne 0) { throw "Failed: $display" }
}

Push-Location $repoRoot
try {
    $st = git -C $mkmLife status --porcelain
    if (-not $st) {
        Write-Host "[INFO] mkm-life working tree clean; skip submodule commit."
    } else {
        $staged = git -C $mkmLife diff --cached --name-only
        if (-not $staged) {
            Write-Host "[STEP] staging mkm-life oracle-sphere files"
            Invoke-Git $mkmLife @(
                "add",
                "lib/oracle-sphere-internal-envelope.ts",
                "lib/runtime-env.ts",
                "lib/oracle-sphere-full-lens-preview.ts",
                "app/api/v1/oracle-sphere/full-envelope/route.ts",
                "scripts/Deploy-CloudflareMkmlife.ps1",
                "scripts/smoke-magic-orb-oracle-sphere-live.mjs",
                "scripts/smoke-oracle-sphere-preview-token-live.mjs",
                "scripts/Sync-MkmlifeInternalEnvelopeKv_v1.ps1",
                "scripts/Sync-MkmlifePublicEnvelopeAssets_v1.ps1",
                "tests/oracle-sphere-paid-access.test.mjs",
                "package.json",
                ".env.local.example",
                "data/internal/three_lens_sphere_envelope_v1.json",
                "public/data/three_lens_sphere_envelope_public_v1.json"
            )
        }
        Invoke-Git $mkmLife @(
            "commit",
            "-m",
            "fix(oracle-sphere): KV-backed full envelope + deploy hardening"
        )
        Invoke-Git $mkmLife @("push", "origin", "main")
        $sha = git -C $mkmLife rev-parse --short HEAD
        Write-Host "[OK] mkm-life pushed at $sha"
    }

    if (-not $SkipMonorepo) {
        Invoke-Git $repoRoot @("add", "scripts/probe_mkmlife_magic_orb_live_v1.py", "projects/mkm/mkm-life")
        $monoStaged = git -C $repoRoot diff --cached --name-only
        if ($monoStaged) {
            Invoke-Git $repoRoot @(
                "commit",
                "-m",
                "chore(mkmlife): oracle-sphere KV deploy + live probe contract"
            )
            if (-not $DryRun) {
                & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\push-internal.ps1")
            } else {
                Write-Host "[DRY] push-internal.ps1"
            }
        } else {
            Write-Host "[INFO] monorepo nothing to commit."
        }
    }
} finally {
    Pop-Location
}

Write-Host "[DONE] Invoke-MkmLifeOracleSphereCommitPush_v1"
