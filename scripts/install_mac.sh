#!/bin/bash
# 린쌤 자동업로드 설치 (macOS)
# 사용: bash scripts/install_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

say() { printf "\n\033[1m%s\033[0m\n" "$1"; }

say "1/6 필요한 프로그램 확인"
if ! command -v brew >/dev/null; then
  echo "Homebrew 가 없습니다. https://brew.sh 안내대로 먼저 설치한 뒤 다시 실행해 주세요."; exit 1
fi
command -v ffmpeg >/dev/null || brew install ffmpeg
command -v python3 >/dev/null || brew install python@3.12
[ -d "/Applications/Google Chrome.app" ] || echo "※ 크롬이 없습니다. browser 방식으로 올릴 때만 필요합니다."
if [ ! -d "/Applications/Aside.app" ]; then
  echo "※ Aside 앱이 없습니다. https://aside.com/download 에서 받아 설치하고, 선생님 계정으로 로그인한 뒤 다시 실행해 주세요."
  open "https://aside.com/download" 2>/dev/null || true
fi
if ! command -v aside >/dev/null && [ ! -x "$HOME/.local/bin/aside" ]; then
  echo "Aside 명령줄 도구(CLI)를 설치합니다 (공식 설치 스크립트)."
  curl -fsSL https://releases.aside.com/install.sh | bash
fi
export PATH="$HOME/.local/bin:$PATH"

say "2/6 파이썬 환경 만들기"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt -r requirements-browser.txt

say "3/6 설정 파일"
if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  echo "config.yaml 을 만들었습니다. 채널명·폴더·수업 안내·연락처를 채워 주세요."
fi

say "4/6 작업 폴더 만들기"
.venv/bin/python - <<'EOF'
from autopost import config as C
cfg = C.load(); f = C.folders(cfg); f.ensure(); print("작업 폴더:", f.base)
EOF

say "5/6 30분마다 자동 실행 등록 (launchd)"
PLIST="$HOME/Library/LaunchAgents/kr.linssam.autopost.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.linssam-autopost"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>kr.linssam.autopost</string>
  <key>ProgramArguments</key><array>
    <string>$ROOT/.venv/bin/python</string><string>-m</string><string>autopost</string><string>tick</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/.linssam-autopost/launchd.out</string>
  <key>StandardErrorPath</key><string>$HOME/.linssam-autopost/launchd.err</string>
</dict></plist>
EOF
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "등록했습니다. (해제: launchctl unload $PLIST)"

say "6/6 Claude 스킬 연결"
mkdir -p "$HOME/.claude/skills" "$HOME/.claude/youtube"
for s in .claude/skills/*; do ln -sfn "$ROOT/$s" "$HOME/.claude/skills/$(basename "$s")"; done
[ -f "$HOME/.claude/youtube/voice.template.md" ] || cp .claude/youtube/voice.template.md "$HOME/.claude/youtube/"
echo "스킬: $(ls .claude/skills | tr '\n' ' ')"

say "Aside 연결 확인"
if aside repl "console.log('@@ASIDE_OK@@')" 2>/dev/null | grep -q "@@ASIDE_OK@@"; then
  echo "Aside 연결 확인됨."
else
  echo "※ Aside 에 연결하지 못했습니다. Aside 앱을 켜고 로그인한 뒤 터미널에서 'aside login' 을 한 번 실행해 주세요."
fi

say "설치 끝"
cat <<EOF
- 구글 드라이브의 작업 폴더에 영상을 넣으면 30분 안에 편집되고, 정해진 요일·시간에 올라갑니다.
- 편집 결과만 먼저 보려면:  .venv/bin/python -m autopost edit "영상파일.mp4"
- 대기열 보기:              .venv/bin/python -m autopost status
- 기록:                     ~/.linssam-autopost/log.txt
EOF
