# Start Next dev simulating no1kmedi.com apex — localhost → /ask (대국민 한의학 AI).
# Usage (from projects/no1kmedi): powershell -File scripts/dev-no1kmedi-apex.ps1
$ErrorActionPreference = "Stop"
$env:MKM_DEV_SIMULATE_NO1KMEDI_APEX = "1"
$env:MKM_DEV_SIMULATE_NO1KMEDI_CLINIC = ""
$env:MKM_DEV_SIMULATE_NO1KMEDI_HOST = "1"
$port = if ($env:PORT) { $env:PORT } else { "3011" }
Write-Host "MKM_DEV_SIMULATE_NO1KMEDI_APEX=1 — open http://localhost:${port}/ (redirects to /ask)"
npx next dev -p $port
