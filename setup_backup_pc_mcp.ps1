# 보조 PC MCP 설정 자동 생성 스크립트
# 메인 PC 영향 없이 보조 PC 전용 설정 생성

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "보조 PC MCP 설정 자동 생성" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 경로 확인
$mainPcConfig = "\\desktop-2511\workspace\.cursor\mcp.json"
$backupPcConfig = "Z:\workspace\.cursor\mcp.json.backup_pc"
$backupPcDir = "Z:\workspace\.cursor"

# 메인 PC 설정 파일 확인
if (-not (Test-Path $mainPcConfig)) {
    Write-Host "❌ 메인 PC 설정 파일을 찾을 수 없습니다: $mainPcConfig" -ForegroundColor Red
    Write-Host "   네트워크 공유 폴더가 올바르게 매핑되었는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 메인 PC 설정 파일 확인: $mainPcConfig" -ForegroundColor Green

# 2. 보조 PC 디렉토리 생성
if (-not (Test-Path $backupPcDir)) {
    New-Item -ItemType Directory -Path $backupPcDir -Force | Out-Null
    Write-Host "✅ 디렉토리 생성: $backupPcDir" -ForegroundColor Green
}

# 3. 메인 PC 설정 파일 읽기
Write-Host "메인 PC 설정 파일 읽는 중..." -ForegroundColor Cyan
try {
    $mcpConfig = Get-Content $mainPcConfig -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "✅ 설정 파일 읽기 성공" -ForegroundColor Green
} catch {
    Write-Host "❌ 설정 파일 읽기 실패: $_" -ForegroundColor Red
    exit 1
}

# 4. 경로 변경 함수
function Update-Paths {
    param($config)
    
    # JSON을 문자열로 변환하여 경로 변경
    $jsonString = $config | ConvertTo-Json -Depth 100
    
    # C:\workspace → Z:\workspace 변경
    $jsonString = $jsonString -replace 'C:\\workspace', 'Z:\workspace'
    $jsonString = $jsonString -replace 'C:/workspace', 'Z:/workspace'
    
    # 환경변수 WORKSPACE_ROOT 변경
    $jsonString = $jsonString -replace '"WORKSPACE_ROOT"\s*:\s*"C:\\\\workspace"', '"WORKSPACE_ROOT": "Z:\\workspace"'
    $jsonString = $jsonString -replace '"WORKSPACE_ROOT"\s*:\s*"C:/workspace"', '"WORKSPACE_ROOT": "Z:/workspace"'
    
    # PYTHONPATH 변경
    $jsonString = $jsonString -replace '"PYTHONPATH"\s*:\s*"C:\\\\workspace"', '"PYTHONPATH": "Z:\\workspace"'
    $jsonString = $jsonString -replace '"PYTHONPATH"\s*:\s*"C:/workspace"', '"PYTHONPATH": "Z:/workspace"'
    
    # Qdrant URL 확인 및 변경 (VPS 사용 권장)
    # localhost:6333 → VPS 또는 메인 PC 네트워크 주소
    $jsonString = $jsonString -replace 'http://localhost:6333', 'http://148.230.97.246:6333'
    $jsonString = $jsonString -replace '"http://127\.0\.0\.1:6333"', '"http://148.230.97.246:6333"'
    
    # JSON 파싱
    try {
        $updatedConfig = $jsonString | ConvertFrom-Json
        return $updatedConfig
    } catch {
        Write-Host "⚠️ JSON 파싱 경고: $_" -ForegroundColor Yellow
        Write-Host "원본 설정을 사용합니다." -ForegroundColor Yellow
        return $config
    }
}

# 5. 경로 변경 적용
Write-Host "경로 변경 중 (C:\workspace → Z:\workspace)..." -ForegroundColor Cyan
$updatedConfig = Update-Paths -config $mcpConfig
Write-Host "✅ 경로 변경 완료" -ForegroundColor Green

# 6. 보조 PC 설정 파일 저장
Write-Host "보조 PC 설정 파일 저장 중..." -ForegroundColor Cyan
try {
    $updatedConfig | ConvertTo-Json -Depth 100 | Set-Content -Path $backupPcConfig -Encoding UTF8
    Write-Host "✅ 설정 파일 저장 완료: $backupPcConfig" -ForegroundColor Green
} catch {
    Write-Host "❌ 설정 파일 저장 실패: $_" -ForegroundColor Red
    exit 1
}

# 7. 환경변수 설정 (현재 세션 + 영구 설정)
Write-Host ""
Write-Host "환경변수 설정 중..." -ForegroundColor Cyan

# 현재 세션 환경변수 설정
$env:WORKSPACE_ROOT = "Z:\workspace"
$env:PYTHONPATH = "Z:\workspace"
$env:QDRANT_URL = "http://148.230.97.246:6333"
Write-Host "✅ 현재 세션 환경변수 설정 완료" -ForegroundColor Green

# 영구 환경변수 설정 (사용자 레벨)
Write-Host "영구 환경변수 설정 중..." -ForegroundColor Cyan
try {
    [System.Environment]::SetEnvironmentVariable("WORKSPACE_ROOT", "Z:\workspace", "User")
    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", "Z:\workspace", "User")
    [System.Environment]::SetEnvironmentVariable("QDRANT_URL", "http://148.230.97.246:6333", "User")
    Write-Host "✅ 영구 환경변수 설정 완료 (재부팅 후에도 유지)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 영구 환경변수 설정 실패: $_" -ForegroundColor Yellow
    Write-Host "   현재 세션 환경변수는 정상 작동합니다." -ForegroundColor Yellow
}

# 8. Qdrant 연결 테스트
Write-Host ""
Write-Host "Qdrant 연결 테스트 중..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://148.230.97.246:6333/collections" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "✅ Qdrant 연결 성공" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Qdrant 연결 실패: $_" -ForegroundColor Yellow
    Write-Host "   VPS Qdrant가 실행 중인지 확인하세요." -ForegroundColor Yellow
}

# 9. 동기화 스크립트 생성 (보조 PC + 메인 PC 모두에 생성)
Write-Host ""
Write-Host "동기화 스크립트 생성 중..." -ForegroundColor Cyan
$syncScriptPath = "Z:\workspace\sync_to_main_pc.ps1"
$syncScriptMainPc = "\\desktop-2511\workspace\sync_to_main_pc.ps1"
$syncScript = @"
# 메인 PC에서 실행: 보조 PC 작업 내용을 로컬 Qdrant로 동기화
# 사용법: 메인 PC에서 PowerShell로 실행
#   cd C:\workspace
#   .\sync_to_main_pc.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "보조 PC 작업 내용 동기화 시작" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Z: 드라이브 확인
`$zDrivePath = "Z:\workspace"
if (-not (Test-Path `$zDrivePath)) {
    Write-Host "❌ Z: 드라이브를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "   네트워크 공유 폴더가 올바르게 매핑되었는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Z: 드라이브 확인: `$zDrivePath" -ForegroundColor Green

# 2. Python 스크립트 실행 (전수 벡터 인덱싱)
Write-Host ""
Write-Host "전수 벡터 인덱싱 실행 중..." -ForegroundColor Cyan
Write-Host "  (이 작업은 몇 분이 걸릴 수 있습니다)" -ForegroundColor Yellow

try {
    # 워크스페이스 인덱싱 서비스 사용
    `$pythonScript = "C:\workspace\scripts\index_workspace_batch.py"
    
    if (Test-Path `$pythonScript) {
        Write-Host "Python 스크립트 실행: `$pythonScript" -ForegroundColor Cyan
        
        # Python 경로 확인
        `$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not `$pythonCmd) {
            `$pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
        }
        
        if (`$pythonCmd) {
            & `$pythonCmd.Name `$pythonScript
            if (`$LASTEXITCODE -eq 0) {
                Write-Host "✅ 벡터 인덱싱 완료" -ForegroundColor Green
            } else {
                Write-Host "⚠️ 인덱싱 중 오류 발생 (종료 코드: `$LASTEXITCODE)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ Python을 찾을 수 없습니다." -ForegroundColor Red
            Write-Host "   MCP 도구를 사용하세요: index_workspace" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️ Python 스크립트를 찾을 수 없습니다: `$pythonScript" -ForegroundColor Yellow
        Write-Host "   MCP 도구를 사용하세요: index_workspace" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "   MCP 도구 사용 방법:" -ForegroundColor Cyan
        Write-Host "   1. Cursor에서 Ctrl+Shift+P" -ForegroundColor White
        Write-Host "   2. 'MCP: Execute Tool' 선택" -ForegroundColor White
        Write-Host "   3. Tool: index_workspace" -ForegroundColor White
        Write-Host "   4. Parameters: {} (기본값 사용)" -ForegroundColor White
    }
} catch {
    Write-Host "❌ 인덱싱 실행 실패: `$_" -ForegroundColor Red
    Write-Host "   MCP 도구를 사용하세요: index_workspace" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "동기화 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "  • 메인 PC에서 벡터 검색 테스트" -ForegroundColor White
Write-Host "  • 명령어: search_workspace (보조 PC 작업 내용 검색)" -ForegroundColor Cyan
Write-Host ""
"@

# 보조 PC에 동기화 스크립트 생성
try {
    Set-Content -Path $syncScriptPath -Value $syncScript -Encoding UTF8
    Write-Host "✅ 동기화 스크립트 생성 완료 (보조 PC): $syncScriptPath" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 동기화 스크립트 생성 실패 (보조 PC): $_" -ForegroundColor Yellow
}

# 메인 PC에도 동기화 스크립트 복사 (선택사항)
try {
    if (Test-Path "\\desktop-2511\workspace") {
        Set-Content -Path $syncScriptMainPc -Value $syncScript -Encoding UTF8
        Write-Host "✅ 동기화 스크립트 생성 완료 (메인 PC): $syncScriptMainPc" -ForegroundColor Green
    } else {
        Write-Host "⚠️ 메인 PC 경로 접근 불가 (정상, 보조 PC에서만 실행 중)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ 메인 PC 스크립트 생성 실패 (선택사항): $_" -ForegroundColor Yellow
}

# 10. 최종 안내
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ VPS 중심 설정 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🏛️ Nitro 전략 적용:" -ForegroundColor Yellow
Write-Host "  • Qdrant: VPS (http://148.230.97.246:6333)" -ForegroundColor White
Write-Host "  • 파일: Z: 드라이브 (실시간 공유)" -ForegroundColor White
Write-Host "  • 동기화: 데일리 벡터 인덱싱 (메인 PC에서)" -ForegroundColor White
Write-Host "  • 환경변수: 영구 설정 완료 (재부팅 후에도 유지)" -ForegroundColor White
Write-Host ""
Write-Host "다음 단계:" -ForegroundColor Yellow
Write-Host "1. Cursor를 재시작하세요" -ForegroundColor White
Write-Host "2. Cursor 설정에서 MCP 파일을 다음으로 지정:" -ForegroundColor White
Write-Host "   $backupPcConfig" -ForegroundColor Cyan
Write-Host "3. Ctrl+Shift+P → 'MCP: Show Server Status'로 확인" -ForegroundColor White
Write-Host ""
Write-Host "📋 데일리 동기화:" -ForegroundColor Yellow
Write-Host "  • 보조 PC 작업 후 메인 PC에서 동기화 실행" -ForegroundColor White
Write-Host "  • 방법 1: 스크립트 실행 - C:\workspace\sync_to_main_pc.ps1" -ForegroundColor Cyan
Write-Host "  • 방법 2: MCP 도구 - index_workspace (메인 PC에서)" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️ 중요: 메인 PC의 mcp.json은 절대 수정하지 마세요!" -ForegroundColor Red
Write-Host ""

