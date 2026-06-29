# Oracle-sphere local live loop — prefer Invoke-MkmlifeDesignLiveDev_v1.ps1 -Lane oracle|all
param(
  [switch]$SkipDevStart,
  [switch]$VerifyOnly
)

& (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts\Invoke-MkmlifeDesignLiveDev_v1.ps1') -Lane oracle @PSBoundParameters