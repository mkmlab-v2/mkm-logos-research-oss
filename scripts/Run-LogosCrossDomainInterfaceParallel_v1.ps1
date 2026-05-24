# Parallel CDIM Phase 1: independent lenses -> fusion stub -> cross-lens RAG -> CDIM assemble.
# Does not tag Bible corpus with ohaeng. [HYPO] research_only NON_GATING.
param(
    [switch]$SkipLens,
    [switch]$SkipFusion,
    [switch]$SkipCrossRag,
    [switch]$SkipStateMapping,
    [switch]$SkipConceptBridge,
    [switch]$Validate,
    [string]$WorkspaceRoot = "C:\workspace"
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = "py"
if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { $py = "python" }

$jobs = @()

if (-not $SkipLens) {
    Write-Host "==> lenses (parallel)" -ForegroundColor Cyan
    $lensSpecs = @(
        @{ Name = "lens_myeongni"; Args = "scripts/run_lens_myeongni.py" },
        @{ Name = "lens_sasang"; Args = "scripts/run_lens_sasang.py" },
        @{ Name = "lens_logos"; Args = "scripts/run_lens_logos.py --allow-fallback" }
    )
    $procs = foreach ($spec in $lensSpecs) {
        Start-Process -FilePath $py -ArgumentList $spec.Args -WorkingDirectory $WorkspaceRoot -PassThru -NoNewWindow
    }
    $procs | Wait-Process
    foreach ($i in 0..($lensSpecs.Count - 1)) {
        if ($procs[$i].ExitCode -ne 0) {
            throw "$($lensSpecs[$i].Name) failed exit $($procs[$i].ExitCode)"
        }
    }
}

if (-not $SkipFusion) {
    Write-Host "==> fusion_stub" -ForegroundColor Cyan
    & $py scripts/report_independent_lens_fusion_stub_v0.py
    if ($LASTEXITCODE -ne 0) { throw "fusion_stub failed" }
}

if (-not $SkipCrossRag) {
    Write-Host "==> cross_lens_rag" -ForegroundColor Cyan
    & $py scripts/build_cross_lens_rag_fusion_v1.py
    if ($LASTEXITCODE -ne 0) { throw "cross_lens_rag failed" }
}

$assembleArgs = @("scripts/assemble_logos_cross_domain_interface_v1.py")
if ($SkipCrossRag) { $assembleArgs += "--no-cross-rag" }
if ($SkipStateMapping) { $assembleArgs += "--no-state-mapping" }
if ($SkipConceptBridge) { $assembleArgs += "--no-concept-bridge" }
else { $assembleArgs += "--use-bridge-registry" }
if ($Validate) { $assembleArgs += "--validate" }

Write-Host "==> cdim_assemble" -ForegroundColor Cyan
& $py @assembleArgs
if ($LASTEXITCODE -ne 0) { throw "cdim_assemble failed" }

Write-Host "==> cdim_digest" -ForegroundColor Cyan
& $py scripts/materialize_logos_cross_domain_interface_digest_v1.py
if ($LASTEXITCODE -ne 0) { throw "cdim_digest failed" }

Write-Host "OK: logos_cross_domain_interface_latest.json + digest MD" -ForegroundColor Green
