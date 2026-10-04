# 린쌤 자동업로드 설치 (Windows)
# 사용: PowerShell 에서  powershell -ExecutionPolicy Bypass -File scripts\install_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$Root = (Get-Location).Path

function Say($m) { Write-Host "`n$m" -ForegroundColor Cyan }

Say "1/6 필요한 프로그램 확인"
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements }
Write-Host "ffmpeg 이나 python 을 방금 설치했다면 PowerShell 을 닫았다가 다시 열고 이 스크립트를 한 번 더 실행해 주세요."

Say "2/6 파이썬 환경 만들기"
python -m venv .venv
.\.venv\Scripts\python -m pip install -q --upgrade pip
.\.venv\Scripts\python -m pip install -q -r requirements.txt -r requirements-browser.txt

Say "3/6 설정 파일"
if (-not (Test-Path config.yaml)) { Copy-Item config.example.yaml config.yaml; Write-Host "config.yaml 을 만들었습니다. 채널명·폴더·수업 안내·연락처를 채워 주세요." }

Say "4/6 작업 폴더 만들기"
.\.venv\Scripts\python -c "from autopost import config as C; cfg=C.load(); f=C.folders(cfg); f.ensure(); print('작업 폴더:', f.base)"

Say "5/6 30분마다 자동 실행 등록 (작업 스케줄러)"
$action = New-ScheduledTaskAction -Execute "$Root\.venv\Scripts\python.exe" -Argument "-m autopost tick" -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "LinssamAutopost" -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "등록했습니다. (해제: Unregister-ScheduledTask -TaskName LinssamAutopost)"

Say "6/6 Claude 스킬 연결"
$skills = "$env:USERPROFILE\.claude\skills"
New-Item -ItemType Directory -Force -Path $skills, "$env:USERPROFILE\.claude\youtube" | Out-Null
Get-ChildItem .claude\skills -Directory | ForEach-Object { Copy-Item $_.FullName "$skills\$($_.Name)" -Recurse -Force }
Copy-Item .claude\youtube\voice.template.md "$env:USERPROFILE\.claude\youtube\" -Force

Say "설치 끝"
Write-Host "편집 결과만 먼저 보기:  .\.venv\Scripts\python -m autopost edit `"영상파일.mp4`""
Write-Host "대기열 보기:            .\.venv\Scripts\python -m autopost status"
