# WSL Nemotron readiness — GPU, venv path, train script (no secrets printed)
param(
    [string] $Distro = 'Ubuntu-24.04',
    [switch] $OutJson
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$outPath = Join-Path $root 'reports\nvidia_nemotron_wsl_readiness_latest.json'

$bash = 'ROOT=/mnt/c/workspace; echo distro_ok=1; (command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1) || echo gpu=missing; test -f $ROOT/scripts/wsl/nemotron_local_setup_and_train_v1.sh && echo bootstrap=ok || echo bootstrap=missing; test -f $ROOT/data/nvidia/nemotron-local/nemotron_qlora_train_v1.py && echo train_py=ok || echo train_py=missing; test -d $ROOT/.venv-wsl-nemotron && echo venv=present || echo venv=absent'

# WSL may emit non-fatal stderr (e.g. systemd user session); keep Stop elsewhere.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$lines = @(wsl -d $Distro -e bash -lc $bash 2>&1)
$ErrorActionPreference = $prevEap
$lines = @($lines | ForEach-Object { "$_" })
$gpu = ($lines | Where-Object { $_ -match 'Ti|GeForce|RTX' } | Select-Object -First 1)
$doc = [ordered]@{
    schema           = 'nvidia_nemotron_wsl_readiness_v1'
    finished_at_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    wsl_distro       = $Distro
    lines            = $lines
    gpu_line         = "$gpu"
    bootstrap_ok     = ($lines -match 'bootstrap=ok').Count -gt 0
    train_py_ok      = ($lines -match 'train_py=ok').Count -gt 0
    venv_present     = ($lines -match 'venv=present').Count -gt 0
    ready            = ($gpu -and ($lines -match 'bootstrap=ok') -and ($lines -match 'train_py=ok'))
}
$doc | ConvertTo-Json -Depth 5 | Set-Content -Path $outPath -Encoding utf8
if ($OutJson) { Get-Content $outPath -Raw }
if (-not $doc.ready) { exit 2 }
Write-Host "[OK] WSL Nemotron readiness -> $outPath"
exit 0
