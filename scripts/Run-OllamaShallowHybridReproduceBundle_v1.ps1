#Requires -Version 5.1
<#
.SYNOPSIS
  ~10 min Hybrid Memory OS reproduce bundle (offline pytest + optional live Ollama).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-OllamaShallowHybridReproduceBundle_v1.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-OllamaShallowHybridReproduceBundle_v1.ps1 -SkipOllama
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-OllamaShallowHybridReproduceBundle_v1.ps1 -IncludeDeepLive
#>
param(
    [switch]$SkipOllama,
    [switch]$IncludeDeepLive,
    [string]$Model = "mkm-shallow-router-v1"
)

$ErrorActionPreference = "Stop"
Set-Location "C:\workspace"

$pyArgs = @("scripts/run_ollama_shallow_hybrid_reproduce_bundle_v1.py", "--model", $Model)
if ($SkipOllama) { $pyArgs += "--skip-ollama" }
if ($IncludeDeepLive) { $pyArgs += "--include-deep-live" }

& py @pyArgs
exit $LASTEXITCODE
